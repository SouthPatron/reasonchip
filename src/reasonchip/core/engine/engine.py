# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

from __future__ import annotations

import typing
import logging
import asyncio

from .. import exceptions as rex


log = logging.getLogger("reasonchip.core.engine.engine")

# -------------------------- TYPES ------------------------------------------


@typing.runtime_checkable
class WorkflowStep(typing.Protocol):
    """
    Protocol for a workflow step.
    """

    def __call__(
        self,
        context: EngineContext,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> typing.Awaitable[typing.Any]: ...


# -------------------------- SUPPORT CLASSES --------------------------------


class EngineContext:
    """
    A context for the workflow engine which is passed to each step in the
    workflow.
    """

    def __init__(self):
        """
        Constructor.
        """
        self._lock: asyncio.Lock = asyncio.Lock()
        self._stack: typing.List[str] = []
        self._state: typing.Dict[str, typing.Any] = {}
        self._cache: typing.Dict[str, WorkflowStep] = {}

    @property
    def state(self) -> typing.Dict[str, typing.Any]:
        """
        Return the state object of the context.

        :return: The state object.
        """
        return self._state

    async def branch(
        self,
        name: str,
        *args,
        **kwargs,
    ) -> typing.Any:
        """
        Call a workflow step by its name with parameters.

        :param name: The name of the workflow step to call.
        :param args: Positional arguments to pass to the step.
        :param kwargs: Keyword arguments to pass to the step.

        :return: The return value of the step.
        """

        log.debug(
            f"Calling workflow step '{name}' with args: {args} and kwargs: {kwargs}"
        )

        # Turn the name into a fully qualified name.
        fqn: str = self._resolve(name)

        log.debug(f"Resolved workflow step '{name}' to '{fqn}'")

        # Resolve the workflow step.
        step = await self._fetch_callable(fqn)

        # Turn the step into a callable.
        self._stack.append(fqn)

        try:
            log.debug(f"Executing workflow step: '{fqn}'")

            # Call the step with the provided arguments.
            rc = await step(self, *args, **kwargs)

            log.debug(f"Workflow step '{fqn}' returned: {rc}")

            return rc

        except rex.RestartEngineException as e:
            # Make sure we resolve at the current stack level
            log.debug(
                f"Workflow step '{fqn}' raised RestartEngineException: {e}"
            )

            e.name = self._resolve(e.name)
            raise

        finally:
            log.debug(f"Finished executing workflow step: '{fqn}'")

            # Pop the current step from the stack, regardless
            self._stack.pop()

    def _resolve(self, name: str) -> str:
        """
        Resolve a workflow step name to a fully qualified name.

        NOTE: This supports dot notation for relative paths. Same as Python.

        :param name: The name of the workflow step to resolve.

        :return: The fully qualified name of the workflow step.
        """

        # Nothing to do here.
        if not self._stack:
            return name

        # Count the relative dots (e.g., "..foo.bar" -> ["", "", "foo", "bar"])
        parts = name.split(".")
        num_dots = 0
        for part in parts:
            if part != "":
                num_dots += 1
            else:
                break

        # If it's already fully qualified, return it as is.
        if num_dots == 0:
            return name

        # Resolve any relative paths
        current = self._stack[-1].split(".")
        if num_dots > len(current):
            raise rex.WorkflowNotFoundException(name)

        base = current[: len(current) - num_dots]
        tail = parts[num_dots:]
        return ".".join(base + tail)

    async def _fetch_callable(self, fqn: str) -> WorkflowStep:

        try:
            # Check if we already have this step cached.
            async with self._lock:
                if fqn in self._cache:
                    return self._cache[fqn]

                # Discover the module and function name from the FQN.
                module_path, _, func_name = fqn.rpartition(".")
                if not module_path or not func_name:
                    raise rex.WorkflowNotFoundException(fqn)

                # Try to import the module and get the function.
                mod = __import__(module_path, fromlist=[func_name])
                func = getattr(mod, func_name)

                # Make sure it's a WorkflowStep callable
                if not isinstance(func, WorkflowStep):
                    raise RuntimeError(
                        f"Workflow step '{fqn}' is not a valid callable."
                    )

                self._cache[fqn] = func
                return func

        except Exception as e:
            log.error(f"Failed to import workflow step '{fqn}': {e}")
            raise rex.WorkflowNotFoundException(fqn) from e


# -------------------------- ENGINE ITSELF ----------------------------------


class Engine:
    """
    A class with a big name and a little job.
    """

    async def run(
        self,
        entry: str,
        *args,
        **kwargs,
    ) -> typing.Any:
        """
        Runs a workflow step with the given context and parameters.

        :param entry: The name of the workflow step to run.
        :param args: Positional arguments to pass to the step.
        :param kwargs: Keyword arguments to pass to the step.

        :return: The return value of the workflow step.
        """

        t_entry = entry
        t_args = args
        t_kwargs = kwargs

        context: EngineContext = EngineContext()

        while True:

            try:
                rc = await context.branch(
                    t_entry,
                    *t_args,
                    **t_kwargs,
                )
                return rc

            except rex.RestartEngineException as e:
                t_entry = e.name
                t_args = e.args
                t_kwargs = e.kwargs

                log.debug(
                    f"Top-level restarting workflow step '{t_entry}' with args: {t_args} and kwargs: {t_kwargs}"
                )

                continue

            except rex.TerminateEngineException as e:
                log.debug(
                    f"Top-level terminating workflow step '{t_entry}' with return code: {e.rc}"
                )
                return e.rc
