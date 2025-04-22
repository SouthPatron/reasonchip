# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import enum
import asyncio

from collections.abc import Iterable, Sized

from pydantic import ValidationError

from .. import exceptions as rex

from .variables import Variables
from .flow_control import FlowControl

from .registry import Registry
from .parsers import evaluator
from .pipelines import (
    TaskSet,
    ChipTask,
    DispatchPipelineTask,
    ReturnTask,
    DeclareTask,
    CommentTask,
    TerminateTask,
    Task,
    SaveableTask,
    LoopableTask,
    Pipeline,
)


ResolverType = typing.Callable[
    [str], typing.Coroutine[None, None, typing.Optional[Pipeline]]
]


class RunResult(enum.IntEnum):
    OK = 0
    SKIPPED = 10
    RETURN_REQUEST = 20


class Processor:

    def __init__(
        self,
        resolver: ResolverType,
    ):
        self._resolver: ResolverType = resolver

    @property
    def resolver(self) -> ResolverType:
        return self._resolver

    async def run(
        self,
        variables: Variables,
        flow: FlowControl,
    ) -> typing.Any:

        try:
            rc, result = await self._sub_run(variables, flow)

            if rc == RunResult.RETURN_REQUEST:
                return result

        except rex.TerminateRequestException as ex:
            return ex.result

        except rex.ProcessorException as ex:
            raise rex.ProcessorException() from ex

        return None

    async def _sub_run(
        self,
        variables: Variables,
        flow: FlowControl,
    ) -> typing.Tuple[RunResult, typing.Any]:

        i = 0

        # Run the flow
        while flow.has_next():

            # Retrieve the first task in the flow
            task = flow.peek()

            # Run the task
            try:
                rc, result = await self.run_task(
                    task=task,
                    variables=variables,
                )
            except rex.ProcessorException as ex:
                raise rex.NestedProcessorException(task_no=i) from ex

            # The task completed successfully, so remove it.
            flow.pop()

            # Handle normal behaviour
            if rc in [RunResult.OK, RunResult.SKIPPED]:
                continue

            # This is the end of the pipeline
            if rc in [RunResult.RETURN_REQUEST]:
                return (rc, result)

            assert False, "Programmer Error. Unreachable code was reached."

        # Successfull completion. No specific return value
        return (RunResult.OK, None)

    async def run_task(
        self,
        task: Task,
        variables: Variables,
    ) -> typing.Tuple[RunResult, typing.Any]:

        # Comments are easy
        if isinstance(task, CommentTask):
            return (RunResult.SKIPPED, None)

        # The rest of the tasks have a when condition.
        if task.when:
            proceed = evaluator(task.when, variables.vmap)
            if not proceed:
                return (RunResult.SKIPPED, None)

        # Bind the variable
        rc = (RunResult.OK, None)

        # Terminate is requested
        if isinstance(task, TerminateTask):
            fixed_results = variables.interpolate(task.terminate)
            raise rex.TerminateRequestException(fixed_results)

        # Return tasks are easy
        if isinstance(task, ReturnTask):
            return await self._run_returntask(task, variables)

        # Figure out what kind of chip this is
        handlers = {
            TaskSet: self._run_taskset,
            DispatchPipelineTask: self._run_dispatchpipelinetask,
            ChipTask: self._run_chiptask,
            DeclareTask: self._run_declaretask,
        }

        # Run the task
        handler = handlers.get(type(task))
        assert handler is not None

        # A task has its own variable scope.
        new_vars = variables.copy()
        if task.variables:
            new_vars.update(task.variables)

        # Handle the task if we're looping
        async for rc in self._loop(task, new_vars, handler):
            self._handle_task_save(task, new_vars, rc[1], variables)

            # Declarations go into the current context
            if isinstance(task, DeclareTask):
                assert rc[0] == RunResult.OK
                new_vars.update(rc[1])
                variables.update(rc[1])

        return rc

    # --------  LOOP ---------------------------------------------------------

    async def _loop(
        self,
        task: LoopableTask,
        new_vars: Variables,
        handler: typing.Callable,
    ) -> typing.AsyncGenerator[typing.Tuple[RunResult, typing.Any], None]:

        # Do we actually need to loop?
        if task.loop is None:
            rc = await handler(task, new_vars)
            yield rc
            return

        # Get the thing we need to loop over.
        loop_vars = new_vars.interpolate(task.loop)

        # If it's still a string, then it's not a valid loop variable.
        if isinstance(loop_vars, str):
            raise rex.LoopVariableNotIterable()

        # If it's not iterable, then it's also not a good loop variable.
        if not isinstance(loop_vars, Iterable):
            raise rex.LoopVariableNotIterable()

        # If it's not sized, then we can't determine the length of the loop.
        if not isinstance(loop_vars, Sized):
            raise rex.LoopVariableNotIterable()

        # Assume success
        rc = (RunResult.OK, None)

        # And now loop through the loop variables
        total_loops = len(loop_vars)

        new_vars.set("loop.length", total_loops)

        for i, loop_var in enumerate(loop_vars):

            new_vars.set("item", loop_var)
            new_vars.set("loop.index", i + 1)
            new_vars.set("loop.index0", i)
            new_vars.set("loop.first", i == 0)
            new_vars.set("loop.last", i == (total_loops - 1))
            new_vars.set("loop.even", i % 2 == 1)  # Based in loop.index
            new_vars.set("loop.odd", i % 2 == 0)  # Based on loop.index
            new_vars.set("loop.revindex", total_loops - i)
            new_vars.set("loop.revindex0", total_loops - i - 1)

            # Handle the task
            rc = await handler(task, new_vars)
            yield rc

    # --------  INDIVIDUAL CHIP HANDLERS -------------------------------------

    async def _run_returntask(
        self,
        task: ReturnTask,
        variables: Variables,
    ) -> typing.Tuple[RunResult, typing.Any]:

        fixed_rc = variables.interpolate(task.result)
        return (RunResult.RETURN_REQUEST, fixed_rc)

    async def _run_declaretask(
        self,
        task: DeclareTask,
        variables: Variables,
    ) -> typing.Tuple[RunResult, typing.Any]:

        if not isinstance(task.declare, dict):
            raise rex.InvalidChipParametersException(task.name or "unnamed")

        fixed_rc = variables.interpolate(task.declare)
        return (RunResult.OK, fixed_rc)

    async def _run_taskset(
        self,
        task: TaskSet,
        variables: Variables,
    ) -> typing.Tuple[RunResult, typing.Any]:

        # We have been provided a list of tasks to run.
        flow = FlowControl(task.tasks)

        # Run the tasks
        if task.run_async:
            resp = asyncio.create_task(
                self._sub_run(
                    variables=variables,
                    flow=flow,
                )
            )
            return (RunResult.OK, resp)

        _, resp = await self._sub_run(
            variables=variables,
            flow=flow,
        )
        return (RunResult.OK, resp)

    async def _run_dispatchpipelinetask(
        self,
        task: DispatchPipelineTask,
        variables: Variables,
    ) -> typing.Tuple[RunResult, typing.Any]:

        # Load the pipeline
        pipeline = await self.resolver(task.dispatch)
        if pipeline is None:
            raise rex.NoSuchPipelineException(task.dispatch)

        # We have loaded the lists of tasks to run.
        flow = FlowControl(pipeline.tasks)

        # Run the tasks
        if task.run_async:
            resp = asyncio.create_task(
                self._sub_run(
                    variables=variables,
                    flow=flow,
                )
            )
            return (RunResult.OK, resp)

        try:
            _, resp = await self._sub_run(
                variables=variables,
                flow=flow,
            )
        except rex.ProcessorException as ex:
            raise rex.NestedProcessorException(
                pipeline_name=task.dispatch
            ) from ex

        return (RunResult.OK, resp)

    async def _run_chiptask(
        self,
        task: ChipTask,
        variables: Variables,
    ) -> typing.Tuple[RunResult, typing.Any]:

        # Check to see if the chip exists
        chip = Registry.get_chip(task.chip)
        if not chip:
            raise rex.NoSuchChipException(task.chip)

        # Validate and interpolate the chip parameters
        try:
            fixed_params = variables.interpolate(task.params)
            req = chip.request_type.model_validate(fixed_params)
        except ValidationError as ve:
            raise rex.InvalidChipParametersException(
                chip=task.chip,
                errors=ve.errors(),
            )

        # Call the chip ---------------------
        if task.run_async:
            resp = asyncio.create_task(chip.func(req))
            return (RunResult.OK, resp)

        try:
            resp = await chip.func(req)
        except Exception as ex:
            raise rex.ChipException(chip=task.chip) from ex

        return (RunResult.OK, resp)

    # --------  HELPER FUNCTIONS ----------------------------------------------

    def _handle_task_save(
        self,
        task: SaveableTask,
        variables: Variables,
        value: typing.Any,
        dest: typing.Optional[Variables] = None,
    ):
        """
        NOTE: This saves to both the variables and the dest.

        Variables is not interpolated.
        Dest is interpolated.

        NOTE: Not a great method.
        """

        if not task.store_result_as and not task.append_result_into:
            return

        # Prepare the result for elevation
        result = variables.interpolate(value) if dest else None

        if task.store_result_as:
            name = task.store_result_as
            variables.set(name, value)
            if dest:
                dest.set(name, result)

        if task.append_result_into:
            name = task.append_result_into

            if not variables.has(name):
                variables.set(name, [value])
                if dest:
                    dest.set(name, [result])

            else:
                val = variables.get(name)
                if not isinstance(val, list):
                    raise rex.InvalidChipParametersException(
                        f"Variable '{name}' is not a list."
                    )
                val.append(result)

                variables.set(name, val)
                if dest:
                    dest.set(name, val)
