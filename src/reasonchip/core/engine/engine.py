# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

from __future__ import annotations

import typing
import logging
import asyncio
import inspect

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
    ) -> typing.Any: ...


class EngineCallbacks(typing.Protocol):
    """
    Protocol for engine hooks (callbacks).

    Implement any subset of these methods to observe engine activity.
    """

    async def on_step_start(
        self,
        context: EngineContext,
        fqn: str,
        args: typing.Tuple,
        kwargs: typing.Dict,
    ) -> None: ...

    async def on_step_end(
        self,
        context: EngineContext,
        fqn: str,
        result: typing.Any,
    ) -> None: ...

    async def on_restart(
        self,
        context: EngineContext,
        fqn: str,
        args: typing.Tuple,
        kwargs: typing.Dict,
    ) -> None: ...

    async def on_terminate(
        self,
        context: EngineContext,
        fqn: str,
        rc: typing.Any,
    ) -> None: ...

    async def on_error(
        self,
        context: EngineContext,
        fqn: str,
        exc: Exception,
    ) -> None: ...


# -------------------------- SUPPORT CLASSES --------------------------------


class EngineContext:
    """
    A context for the workflow engine which is passed to each step in the
    workflow.
    """

    def __init__(
        self,
        callbacks: typing.Optional[typing.List[EngineCallbacks]] = None,
    ):
        """
        Constructor.
        """
        self._lock: asyncio.Lock = asyncio.Lock()
        self._stack: typing.List[str] = []
        self._state: typing.Dict[str, typing.Any] = {}
        self._cache: typing.Dict[str, WorkflowStep] = {}
        self._callbacks: typing.List[EngineCallbacks] = callbacks or []

    @property
    def state(self) -> typing.Dict[str, typing.Any]:
        """
        Return the state object of the context.

        :return: The state object.
        """
        return self._state

    def add_callbacks(self, callbacks: EngineCallbacks) -> None:
        self._callbacks.append(callbacks)

    def remove_callbacks(self, callbacks: EngineCallbacks) -> None:
        self._callbacks.remove(callbacks)

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

            # Notify callbacks about step start
            await self._notify("on_step_start", fqn, args, kwargs)

            # Call the step with the provided arguments.
            rc = step(self, *args, **kwargs)
            if inspect.iscoroutine(rc):
                rc = await rc

            # Notify callbacks about step end
            await self._notify("on_step_end", fqn, rc)

            log.debug(f"Workflow step '{fqn}' returned: {rc}")
            return rc

        except rex.RestartEngineException as e:
            # Make sure we resolve at the current stack level
            log.debug(
                f"Workflow step '{fqn}' raised RestartEngineException: {e}"
            )

            await self._notify("on_restart", fqn, e.args, e.kwargs)
            e.name = self._resolve(e.name)
            raise

        except rex.TerminateEngineException as e:
            log.debug(
                f"Workflow step '{fqn}' raised TerminateEngineException: {e}"
            )
            await self._notify("on_terminate", fqn, e.rc)
            raise

        except Exception as e:
            log.exception(f"Workflow step '{fqn}' raised an exception: {e}")
            await self._notify("on_error", fqn, e)
            raise

        finally:
            log.debug(f"Finished executing workflow step: '{fqn}'")

            # Pop the current step from the stack, regardless
            self._stack.pop()

    def restart(
        self,
        name: str,
        *args,
        **kwargs,
    ) -> typing.NoReturn:
        """
        Restart the workflow engine at a given step with parameters.

        :param name: The name of the workflow step to restart at.
        :param args: Positional arguments to pass to the step.
        :param kwargs: Keyword arguments to pass to the step.

        :raise RestartEngineException: Always raised to signal a restart.
        """
        log.debug(
            f"Requesting restart of workflow step '{name}' with args: {args} and kwargs: {kwargs}"
        )
        raise rex.RestartEngineException(name, args, kwargs)

    def terminate(
        self,
        rc: typing.Any = 0,
    ) -> typing.NoReturn:
        """
        Terminate the workflow engine with a return code.

        :param rc: The return value of the engine.

        :raise TerminateEngineException: Always raised to signal a termination.
        """
        log.debug(f"Requesting termination of engine with rc: {rc}")
        raise rex.TerminateEngineException(rc)

    # -------------------------- PRIVATE METHODS -----------------------------

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

        # Handle relative imports
        new_parts = name.split(".")
        old_parts = self._stack[-1].split(".")

        # Nothing is relative
        if new_parts[0] != "":
            return name

        # Handle relative paths
        while new_parts[0] == "":
            # We can't go up if there's nothing to go up from.
            if not old_parts:
                raise rex.WorkflowNotFoundException(name)

            old_parts.pop()
            new_parts = new_parts[1:]

        # Join the old parts and new parts to form the fully qualified name.
        new_name = ".".join(old_parts + new_parts)
        return new_name

    async def _fetch_callable(self, fqn: str) -> WorkflowStep:
        async with self._lock:
            if fqn in self._cache:
                return self._cache[fqn]

            func = self._load_callable(fqn)

            self._cache[fqn] = func
            return func

    def _load_callable(self, fqn: str) -> WorkflowStep:
        try:
            # Discover the module and function name from the FQN.
            module_path, _, func_name = fqn.rpartition(".")
            if not module_path or not func_name:
                raise rex.WorkflowNotFoundException(fqn)

            # Try to import the module and get the function.
            log.debug(f"Importing '{func_name}' from module '{module_path}'")
            mod = __import__(module_path, fromlist=[func_name])
            log.debug(f"Successfully imported '{module_path}'")
            func = getattr(mod, func_name, None)

            # Check that func is a module
            if isinstance(func, type(mod)):
                # Look for 'entry' within the module
                log.debug(f"'{func_name}' is a module. Looking for entry.")
                mod = __import__(fqn, fromlist=["entry"])
                func = getattr(mod, "entry", None)

                log.debug(f"Found module '{fqn}' with entry '{func_name}'")

                if not func:
                    log.debug(f"Function 'entry' not found in module '{fqn}'")

            # Make sure it's a WorkflowStep callable
            if not isinstance(func, WorkflowStep):
                raise RuntimeError(
                    f"Workflow step '{fqn}' is not a valid callable."
                )

            return func

        except Exception as e:
            log.error(f"Failed to import workflow step '{fqn}': {e}")
            raise rex.WorkflowNotFoundException(fqn) from e

    async def _notify(self, event: str, *args, **kwargs):
        """
        Call callbacks methods if implemented.
        """
        for callback in self._callbacks:
            fn = getattr(callback, event, None)
            if fn is not None:
                await fn(self, *args, **kwargs)


# -------------------------- ENGINE ITSELF ----------------------------------


class Engine:
    """
    A class with a big name and a little job.
    """

    def __init__(
        self, callbacks: typing.Optional[typing.List[EngineCallbacks]] = None
    ):
        """
        Constructor.
        """
        self._callbacks = callbacks or []

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

        context: EngineContext = EngineContext(callbacks=self._callbacks)

        while True:
            try:
                return await context.branch(
                    t_entry,
                    *t_args,
                    **t_kwargs,
                )

            except rex.RestartEngineException as e:
                assert not context._stack

                t_entry = e.name
                t_args = e.args
                t_kwargs = e.kwargs

                log.debug(
                    f"Top-level restarting workflow step '{t_entry}' with args: {t_args} and kwargs: {t_kwargs}"
                )

                continue

            except rex.TerminateEngineException as e:
                assert not context._stack

                log.debug(
                    f"Top-level terminating workflow step '{t_entry}' with return code: {e.rc}"
                )
                return e.rc
