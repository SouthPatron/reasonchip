# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import enum
import asyncio
import logging

from collections.abc import Iterable, Sized

from pydantic import ValidationError

from .. import exceptions as rex

from ..stack import Stack

from .variables import Variables
from .flow_control import FlowControl
from .registry import Registry
from .parsers import evaluator, executor

from .pipelines import (
    # Generic Task
    Task,
    # Specific Tasks
    AssertTask,
    BranchTask,
    ChipTask,
    CodeTask,
    CommentTask,
    DeclareTask,
    DispatchTask,
    ReturnTask,
    TaskSet,
    TerminateTask,
    # Task Types
    LoopableTask,
    SaveableTask,
    # Pipeline
    Pipeline,
)


ResolverType = typing.Callable[
    [str], typing.Coroutine[None, None, typing.Optional[Pipeline]]
]


log = logging.getLogger("reasonchip.core.engine.processor")


class RunResult(enum.IntEnum):
    OK = 0
    SKIPPED = 10
    RETURN_REQUEST = 20


# --------- Exceptions -------------------------------------------------------


class FlowException(rex.ProcessorException):
    """A flow exception raised from the chip."""

    pass


class TerminateRequestException(FlowException):
    """Raised when everything should terminate."""

    def __init__(self, result: typing.Any):
        self.result = result


class BranchRequestException(FlowException):
    """Raised when a branch request is made."""

    def __init__(
        self,
        entry: str,
        variables: Variables,
    ):
        self.entry = entry
        self.variables = variables


# -------- Processor ---------------------------------------------------------


class Processor:

    def __init__(
        self,
        resolver: ResolverType,
    ):
        self._resolver: ResolverType = resolver
        self._stack: Stack = Stack()

    @property
    def resolver(self) -> ResolverType:
        return self._resolver

    @property
    def stack(self) -> Stack:
        return self._stack

    async def run(
        self,
        variables: Variables,
        entry: str,
    ) -> typing.Any:

        pipeline_name = entry
        new_vars = variables.copy()

        while True:
            try:
                # Fetch the pipeline
                pipeline = await self.resolver(pipeline_name)
                if not pipeline:
                    raise rex.NoSuchPipelineException(pipeline_name)

                # Load the flow control
                flow = FlowControl(flow=pipeline.tasks)

                rc, result = await self._sub_run(
                    frame_name=pipeline_name,
                    variables=new_vars,
                    flow=flow,
                )

                if rc == RunResult.RETURN_REQUEST:
                    return result

                return None

            except TerminateRequestException as ex:
                return ex.result

            except BranchRequestException as ex:
                pipeline_name = ex.entry
                new_vars = ex.variables
                continue

            except rex.ProcessorException as ex:
                ex.stack = self._stack
                raise

    async def _sub_run(
        self,
        frame_name: str,
        variables: Variables,
        flow: FlowControl,
    ) -> typing.Tuple[RunResult, typing.Any]:

        try:
            # New stack frame
            self._stack.push(pipeline=frame_name)

            # Run the flow
            while flow.has_next():

                # Retrieve the first task in the flow
                task = flow.peek()

                # Increment the task number
                self._stack.tick(task=task)

                # Run the task
                rc, result = await self.run_task(
                    task=task,
                    variables=variables,
                )

                # The task completed successfully, so remove it.
                flow.pop()

                # Handle normal behaviour
                if rc in [RunResult.OK, RunResult.SKIPPED]:
                    continue

                # This is the end of the pipeline
                if rc in [RunResult.RETURN_REQUEST]:
                    self._stack.pop()
                    return (rc, result)

                assert False, "Programmer Error. Unreachable code was reached."

            self._stack.pop()

            # Successful completion. No specific return value
            return (RunResult.OK, None)

        except BranchRequestException:
            self._stack.pop()
            raise

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

        # ------------- EASY TASKS ------------------------------------------

        # Terminate is requested
        if isinstance(task, TerminateTask):
            fixed_results = variables.interpolate(task.terminate)
            raise TerminateRequestException(result=fixed_results)

        # Return tasks are easy
        if isinstance(task, ReturnTask):
            return await self._run_returntask(task, variables)

        # DeclareTasks are kinda easy but can loop.
        if isinstance(task, DeclareTask):
            async for rc in self._loop(task, variables, self._run_declaretask):
                assert rc[0] == RunResult.OK
                variables.update(rc[1])

            return rc

        # AssertTasks are easy too
        if isinstance(task, AssertTask):
            async for rc in self._loop(task, variables, self._run_asserttask):
                assert rc[0] == RunResult.OK

            return rc

        # Branch has been requested
        if isinstance(task, BranchTask):
            # No need to make variable copies as we're not going back.
            if task.variables:
                variables.update(task.variables)

            # Parameters are interpolated
            if task.params:
                fixed_results = variables.interpolate(task.params)
                variables.update(fixed_results)

            raise BranchRequestException(
                entry=task.branch,
                variables=variables,
            )

        # ------------- LESS EASY TASKS -------------------------------------

        # Figure out what kind of chip this is
        handlers = {
            TaskSet: self._run_taskset,
            DispatchTask: self._run_dispatchtask,
            ChipTask: self._run_chiptask,
            CodeTask: self._run_codetask,
        }

        # Run the task
        handler = handlers.get(type(task))
        assert handler is not None

        # A task has its own variable scope.
        new_vars = variables.copy()

        # Variables are not interpolated
        if task.variables:
            new_vars.update(task.variables)

        # Parameters are interpolated
        if task.params:
            fixed_results = new_vars.interpolate(task.params)
            new_vars.update(fixed_results)

        # Handle the task if we're looping
        async for rc in self._loop(task, new_vars, handler):
            assert rc[0] == RunResult.OK
            self._handle_task_save(task, rc[1], new_vars, variables)

        assert rc[0] == RunResult.OK

        if task.return_result:
            return (RunResult.RETURN_REQUEST, rc[1])

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
            raise rex.LoopVariableNotIterableException(task.loop)

        # If it's not iterable, then it's also not a good loop variable.
        if not isinstance(loop_vars, Iterable):
            raise rex.LoopVariableNotIterableException(task.loop)

        # If it's not sized, then we can't determine the length of the loop.
        if not isinstance(loop_vars, Sized):
            raise rex.LoopVariableNotIterableException(task.loop)

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

        if task.log:
            if task.log == "info":
                log.info("Returning from pipeline")
            elif task.log == "debug":
                log.info(f"Returning from pipeline: {task.result}")
            elif task.log == "trace":
                log.info(
                    f"Returning from pipeline: {task.result} -> {fixed_rc}"
                )

        return (RunResult.RETURN_REQUEST, fixed_rc)

    async def _run_declaretask(
        self,
        task: DeclareTask,
        variables: Variables,
    ) -> typing.Tuple[RunResult, typing.Any]:

        if not isinstance(task.declare, dict):
            raise rex.InvalidChipParametersException(task.name or "unnamed")

        fixed_rc = variables.interpolate(task.declare)

        if task.log:
            if task.log == "info":
                log.info("Declaring new variables")
            elif task.log == "debug":
                log.info(f"Declaring new variables: {task.declare}")
            elif task.log == "trace":
                log.info(
                    f"Declaring new variables: {task.declare} -> {fixed_rc}"
                )

        return (RunResult.OK, fixed_rc)

    async def _run_asserttask(
        self,
        task: AssertTask,
        variables: Variables,
    ) -> typing.Tuple[RunResult, typing.Any]:

        if isinstance(task.checks, str):
            checks = [task.checks]
        else:
            checks = task.checks

        for c in checks:
            rc = evaluator(c, variables.vmap)
            if rc:
                continue

            if task.log:
                log.info(f"Assertation failed: {c}")

            raise rex.AssertException(c)

        if task.log:
            if task.log == "info":
                log.info("Asserts have passed")
            else:
                log.info(f"Asserts have passed: {task.checks}")

        return (RunResult.OK, None)

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
                    frame_name="<taskset>",
                    variables=variables,
                    flow=flow,
                )
            )
        else:
            _, resp = await self._sub_run(
                frame_name="<taskset>",
                variables=variables,
                flow=flow,
            )

        return (RunResult.OK, resp)

    async def _run_dispatchtask(
        self,
        task: DispatchTask,
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
                    frame_name=task.dispatch,
                    variables=variables,
                    flow=flow,
                )
            )
        else:
            _, resp = await self._sub_run(
                frame_name=task.dispatch,
                variables=variables,
                flow=flow,
            )

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

        # Validate the chip parameters
        try:
            fixed_params = variables.interpolate(task.params)
            req = chip.request_type.model_validate(fixed_params)
        except ValidationError as ve:
            raise rex.InvalidChipParametersException(
                chip=task.chip,
                errors=ve.errors(),
            )

        if task.log:
            if task.log == "info":
                log.info(f"Calling chip: [{task.chip}]")
            elif task.log == "debug":
                log.info(f"Calling chip: [{task.chip}] : [{req}]")
            elif task.log == "trace":
                log.info(f"Calling chip: [{task.chip}] : [{req}]")

        # Call the chip ---------------------
        if task.run_async:
            resp = asyncio.create_task(chip.func(req))
            return (RunResult.OK, resp)

        try:
            resp = await chip.func(req)

            if task.log:
                if task.log == "info":
                    log.info(f"Chip complete: [{task.chip}]")
                elif task.log == "debug":
                    log.info(f"Chip complete: [{task.chip}] : [{req}]")
                elif task.log == "trace":
                    log.info(
                        f"Chip complete: [{task.chip}] : [{req}] -> [{resp}]"
                    )

        except Exception as ex:
            raise rex.ChipException(task.chip) from ex

        return (RunResult.OK, resp)

    async def _run_codetask(
        self,
        task: CodeTask,
        variables: Variables,
    ) -> typing.Tuple[RunResult, typing.Any]:

        if task.log:
            if task.log == "info":
                log.info(f"Executing code")
            elif task.log == "debug":
                log.info(f"Executing code")
            elif task.log == "trace":
                log.info(f"Executing code")

        # Run the code ----------------------
        if task.run_async:
            resp = asyncio.create_task(executor(task.code, variables.vmap))
            return (RunResult.OK, resp)

        try:
            resp = await executor(task.code, variables.vmap)

            if task.log:
                if task.log == "info":
                    log.info(f"Code complete")
                elif task.log == "debug":
                    log.info(f"Code complete")
                elif task.log == "trace":
                    log.info(f"Code complete: [{resp}]")

        except Exception as ex:
            raise rex.CodeExecutionException() from ex

        return (RunResult.OK, resp)

    # --------  HELPER FUNCTIONS ----------------------------------------------

    def _handle_task_save(
        self,
        task: SaveableTask,
        value: typing.Any,
        local_variables: Variables,
        global_variables: Variables,
    ):
        # Always save results as '_'
        local_variables.set("_", value)
        global_variables.set("_", value)

        if (
            not task.store_result_as
            and not task.append_result_into
            and not task.key_result_into
        ):
            return

        # Prepare the result for elevation
        if task.store_result_as:
            name = task.store_result_as
            local_variables.set(name, value)
            global_variables.set(name, value)

        if task.append_result_into:
            name = task.append_result_into

            found, obj = local_variables.get(name)
            if not found:
                obj = [value]
                local_variables.set(name, obj)

            else:
                if not isinstance(obj, list):
                    raise rex.InvalidChipParametersException(
                        f"Variable '{name}' is not a list."
                    )
                obj.append(value)

            global_variables.set(name, obj)

        if task.key_result_into:
            name = task.key_result_into.name
            key_name = task.key_result_into.key

            # Keys are interpolated
            key_name = local_variables.interpolate(key_name)

            found, obj = local_variables.get(name)
            if not found:
                obj = {key_name: value}
                local_variables.set(name, obj)

            else:
                if not isinstance(obj, dict):
                    raise rex.InvalidChipParametersException(
                        f"Variable '{name}' is not a dictionary."
                    )
                obj.update({key_name: value})

            global_variables.set(name, obj)
