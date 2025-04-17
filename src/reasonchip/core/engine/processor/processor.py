#!/usr/bin/env python3
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

from ... import exceptions as rex

from ..context import Variables, FlowControl

from ..registry import Registry
from ..parsers.conditional import evaluate
from ..pipelines import (
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

log = logging.getLogger(__name__)

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
        """
        Initialize the Processor with a resolver function.

        :param resolver: Coroutine function that resolves pipeline names to Pipeline objects.
        """
        self._resolver: ResolverType = resolver
        log.debug(f"Processor initialized with resolver: {resolver}")

    @property
    def resolver(self) -> ResolverType:
        """Resolver property getter."""
        return self._resolver

    async def run(
        self,
        variables: Variables,
        flow: FlowControl,
    ) -> typing.Any:
        """
        Runs the provided flow with given variables and flow control.

        :param variables: Current set of variables to use during execution.
        :param flow: Flow control object managing execution flow.

        :return: Result of the flow execution, or None.
        """
        try:
            rc, result = await self._sub_run(variables, flow)
            log.debug(
                f"Flow run finished with result code {rc}, result {result}"
            )

            if rc == RunResult.RETURN_REQUEST:
                log.info("Return requested with result.")
                return result

        except rex.TerminateRequestException as ex:
            log.info(f"Flow terminated with result: {ex.result}")
            return ex.result

        except rex.ProcessorException as ex:
            log.error("ProcessorException encountered during run.", exc_info=ex)
            raise rex.ProcessorException() from ex

        return None

    async def _sub_run(
        self,
        variables: Variables,
        flow: FlowControl,
    ) -> typing.Tuple[RunResult, typing.Any]:
        """
        Internal method to run the tasks in the flow sequentially.

        :param variables: Variables used during execution.
        :param flow: Flow control object.

        :return: Tuple of RunResult and the result value.
        """
        i = 0

        # Run the flow
        while flow.has_next():

            # Retrieve the first task in the flow
            task = flow.peek()
            log.debug(f"Running task {i}: {task}")

            # Run the task
            try:
                rc, result = await self.run_task(
                    task=task,
                    variables=variables,
                )
                log.debug(
                    f"Task {i} completed with code {rc} and result {result}"
                )
            except rex.ProcessorException as ex:
                log.error(f"ProcessorException in task {i}.", exc_info=ex)
                raise rex.NestedProcessorException(task_no=i) from ex

            # The task completed successfully, so remove it.
            flow.pop()

            # Handle normal behaviour
            if rc in [RunResult.OK, RunResult.SKIPPED]:
                i += 1
                continue

            # This is the end of the pipeline
            if rc in [RunResult.RETURN_REQUEST]:
                log.info(f"ReturnRequest from task {i} with result {result}")
                return (rc, result)

            assert False, "Programmer Error. Unreachable code was reached."

        # Successful completion. No specific return value
        log.info("Flow run completed successfully.")
        return (RunResult.OK, None)

    async def run_task(
        self,
        task: Task,
        variables: Variables,
    ) -> typing.Tuple[RunResult, typing.Any]:
        """
        Runs an individual task using the appropriate handler.

        :param task: The task to run.
        :param variables: Variables available for the task.

        :return: Tuple with RunResult and the result from the task.
        """
        log.debug(f"Running task: {task}")

        # Comments are easy
        if isinstance(task, CommentTask):
            log.debug("Skipping CommentTask.")
            return (RunResult.SKIPPED, None)

        # The rest of the tasks have a when condition.
        if task.when:
            proceed = evaluate(task.when, variables)
            log.debug(f"Task condition evaluated to: {proceed}")
            if not proceed:
                log.debug("Skipping task due to when condition.")
                return (RunResult.SKIPPED, None)

        # Bind the variable
        rc = (RunResult.OK, None)

        # Terminate is requested
        if isinstance(task, TerminateTask):
            fixed_results = variables.interpolate(task.terminate)
            log.info(f"Termination requested with result: {fixed_results}")
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

        log.debug(f"Task completed with result code {rc[0]} and value {rc[1]}")
        return rc

    # --------  LOOP ---------------------------------------------------------

    async def _loop(
        self,
        task: LoopableTask,
        new_vars: Variables,
        handler: typing.Callable,
    ) -> typing.AsyncGenerator[typing.Tuple[RunResult, typing.Any], None]:
        """
        Handles looping over task if loop variable is specified.

        :param task: The loopable task.
        :param new_vars: Variables to be used in the loop.
        :param handler: Callable handler to execute for each iteration.

        :yield: Tuple of RunResult and result from each loop iteration.
        """

        # Do we actually need to loop?
        if task.loop is None:
            rc = await handler(task, new_vars)
            yield rc
            return

        # Get the thing we need to loop over.
        loop_vars = new_vars.interpolate(task.loop)

        # If it's still a string, then it's not a valid loop variable.
        if isinstance(loop_vars, str):
            log.error(f"Invalid loop variable, still a string: {loop_vars}")
            raise rex.LoopVariableNotIterable()

        # If it's not iterable, then it's also not a good loop variable.
        if not isinstance(loop_vars, Iterable):
            log.error(f"Loop variable is not Iterable: {loop_vars}")
            raise rex.LoopVariableNotIterable()

        # If it's not sized, then we can't determine the length of the loop.
        if not isinstance(loop_vars, Sized):
            log.error(f"Loop variable is not Sized: {loop_vars}")
            raise rex.LoopVariableNotIterable()

        # Assume success
        rc = (RunResult.OK, None)

        # And now loop through the loop variables
        total_loops = len(loop_vars)
        log.debug(f"Starting loop with {total_loops} iterations.")

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
        """
        Runs a ReturnTask and returns its result as a return request.

        :param task: The ReturnTask to process.
        :param variables: Variables for interpolation.

        :return: RunResult and the interpolated result.
        """
        fixed_rc = variables.interpolate(task.result)
        log.debug(f"ReturnTask result interpolated: {fixed_rc}")
        return (RunResult.RETURN_REQUEST, fixed_rc)

    async def _run_declaretask(
        self,
        task: DeclareTask,
        variables: Variables,
    ) -> typing.Tuple[RunResult, typing.Any]:
        """
        Runs a DeclareTask, validates declaration dictionary.

        :param task: DeclareTask to run.
        :param variables: Variables for interpolation.

        :return: RunResult and interpolated declaration.
        """
        if not isinstance(task.declare, dict):
            log.error(
                f"Invalid declare parameter for task: {task.name or 'unnamed'}"
            )
            raise rex.InvalidChipParametersException(task.name or "unnamed")

        fixed_rc = variables.interpolate(task.declare)
        log.debug(f"DeclareTask interpolated declaration: {fixed_rc}")
        return (RunResult.OK, fixed_rc)

    async def _run_taskset(
        self,
        task: TaskSet,
        variables: Variables,
    ) -> typing.Tuple[RunResult, typing.Any]:
        """
        Runs a TaskSet either synchronously or asynchronously.

        :param task: The TaskSet to run.
        :param variables: Variables for execution.

        :return: RunResult and response from running the tasks.
        """
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
            log.debug("TaskSet running asynchronously.")
            return (RunResult.OK, resp)

        _, resp = await self._sub_run(
            variables=variables,
            flow=flow,
        )
        log.debug("TaskSet completed synchronously.")
        return (RunResult.OK, resp)

    async def _run_dispatchpipelinetask(
        self,
        task: DispatchPipelineTask,
        variables: Variables,
    ) -> typing.Tuple[RunResult, typing.Any]:
        """
        Dispatches a pipeline task by resolving and executing the dispatch pipeline.

        :param task: The DispatchPipelineTask to run.
        :param variables: Variables used for execution.

        :return: RunResult and response from pipeline execution.
        """
        # Load the pipeline
        pipeline = await self.resolver(task.dispatch)
        if pipeline is None:
            log.error(f"No pipeline found for dispatch: {task.dispatch}")
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
            log.debug("DispatchPipelineTask running asynchronously.")
            return (RunResult.OK, resp)

        try:
            _, resp = await self._sub_run(
                variables=variables,
                flow=flow,
            )
            log.debug(
                f"DispatchPipelineTask '{task.dispatch}' completed synchronously."
            )
        except rex.ProcessorException as ex:
            log.error(
                f"ProcessorException in DispatchPipelineTask '{task.dispatch}'.",
                exc_info=ex,
            )
            raise rex.NestedProcessorException(
                pipeline_name=task.dispatch
            ) from ex

        return (RunResult.OK, resp)

    async def _run_chiptask(
        self,
        task: ChipTask,
        variables: Variables,
    ) -> typing.Tuple[RunResult, typing.Any]:
        """
        Runs a ChipTask by validating parameters and invoking the chip.

        :param task: The ChipTask to run.
        :param variables: Variables for parameter interpolation.

        :return: RunResult and response from the chip function.
        """
        # Check to see if the chip exists
        chip = Registry.get_chip(task.chip)
        if not chip:
            log.error(f"No such chip found: {task.chip}")
            raise rex.NoSuchChipException(task.chip)

        # Validate and interpolate the chip parameters
        try:
            fixed_params = variables.interpolate(task.params)
            req = chip.request_type.model_validate(fixed_params)
            log.debug(
                f"Chip parameters validated for chip '{task.chip}': {req}"
            )
        except ValidationError as ve:
            log.error(
                f"Invalid chip parameters for chip '{task.chip}': {ve.errors()}"
            )
            raise rex.InvalidChipParametersException(
                chip=task.chip,
                errors=ve.errors(),
            )

        # Call the chip ---------------------
        if task.run_async:
            resp = asyncio.create_task(chip.func(req))
            log.debug(f"Chip task for {task.chip} running asynchronously.")
            return (RunResult.OK, resp)

        try:
            resp = await chip.func(req)
            log.debug(f"Chip task for {task.chip} completed synchronously.")
        except Exception as ex:
            log.error(f"Error executing chip '{task.chip}'.", exc_info=ex)
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
        Stores or appends task result into variables or destination context.

        Variables is not interpolated.
        Dest is interpolated.

        NOTE: Not a great method.

        :param task: The task with save instructions.
        :param variables: Variables to store or append result.
        :param value: The value to save.
        :param dest: Optional destination variables to also save into.
        """

        if not task.store_result_as and not task.append_result_into:
            log.debug("No store or append instructions on task.")
            return

        # Prepare the result for elevation
        result = variables.interpolate(value) if dest else None

        if task.store_result_as:
            name = task.store_result_as
            variables.set(name, value)
            if dest:
                dest.set(name, result)
            log.debug(f"Stored result as '{name}'")

        if task.append_result_into:
            name = task.append_result_into

            if not variables.has(name):
                variables.set(name, [value])
                if dest:
                    dest.set(name, [result])
                log.debug(f"Initialized and appended result into list '{name}'")

            else:
                val = variables.get(name)
                if not isinstance(val, list):
                    log.error(
                        f"Variable '{name}' is not a list, cannot append."
                    )
                    raise rex.InvalidChipParametersException(
                        f"Variable '{name}' is not a list."
                    )
                val.append(result)

                variables.set(name, val)
                if dest:
                    dest.set(name, val)
                log.debug(f"Appended result into existing list '{name}'")
