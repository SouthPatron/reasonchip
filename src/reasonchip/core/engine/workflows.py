# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

from __future__ import annotations

import typing
import types
import importlib
import importlib.util
import asyncio
import sys

from pathlib import Path

from .. import exceptions as rex


# -------------------------- CONTEXT ----------------------------------------


class WorkflowContext:
    """
    A placeholder for the workflow context. This will be overriden by
    users of workflows.
    """

    pass


# -------------------------- TYPES ------------------------------------------


@typing.runtime_checkable
class WorkflowStep(typing.Protocol):
    """
    Protocol for a workflow step.
    """

    def __call__(
        self,
        context: WorkflowContext,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> typing.Any: ...


# -------------------------- WORKFLOWS --------------------------------------


class Workflow:
    """
    Represents a workflow, which is a collection of callable steps.
    """

    def __init__(
        self,
        name: str,
        module: types.ModuleType,
    ):
        """
        Initialize a Workflow object.

        :param name: The name of the Workflow
        :param module: The module for the Workflow
        """
        self._lock: asyncio.Lock = asyncio.Lock()
        self._name: str = name
        self._module: types.ModuleType = module
        self._cache: typing.Dict[str, WorkflowStep] = {}

    @property
    def name(self) -> str:
        """
        Name of the workflow.
        """
        return self._name

    @property
    def module(self) -> types.ModuleType:
        """
        Module for the workflow
        """
        return self._module

    async def resolve(self, fqn: str) -> WorkflowStep:
        """
        Retrieves the callable with the fqn.

        :param fqn: Fully qualified name of the callable to resolve.

        :return: The WorkflowStep as found.
        """

        async with self._lock:
            # Hopefully it is already cached.
            if fqn in self._cache:
                return self._cache[fqn]

            # Search for the callable in the module.
            obj = self._module

            parts = fqn.split(".")
            for i in parts:
                obj = getattr(obj, i, None)
                if obj is None:
                    raise rex.WorkflowNotFoundException(fqn)

            # Make sure it's a callable
            if not isinstance(obj, WorkflowStep):
                raise rex.WorkflowStepMalformedException(fqn)

            # Cache the resolved callable for future use.
            self._cache[fqn] = obj
            return obj


class WorkflowSet:
    """
    A collection of workflows
    """

    def __init__(self):
        """
        Initialize a WorkflowSet object.
        """
        self._workflows: typing.Dict[str, Workflow] = {}

    def add(self, workflow: Workflow) -> WorkflowSet:
        """
        Add a workflow to the set.

        :param workflow: The Workflow object to add.
        """
        if workflow.name in self._workflows:
            raise rex.WorkflowAlreadyExistsException(workflow.name)

        self._workflows[workflow.name] = workflow
        return self

    async def resolve(self, fqn: str) -> WorkflowStep:
        """
        Resolve the callable with the given fully qualified name (FQN).

        :param fqn: Fully qualified name of the callable to resolve.

        :return: The WorkflowStep.
        """

        # Split the FQN into parts and check if it has at least two parts.
        parts = fqn.split(".")
        if len(parts) < 2:
            raise rex.WorkflowNotFoundException(fqn)

        name = parts[0]
        rem = ".".join(parts[1:])

        # The workflow needs to exist
        workflow = self._workflows.get(name, None)
        if not workflow:
            raise rex.WorkflowNotFoundException(fqn)

        return await workflow.resolve(rem)


# -------------------------- LOADER -----------------------------------------


class WorkflowLoader:
    """
    Loads the workflow collections from the given path.
    """

    def load_from_path(
        self,
        module_name: str,
        path: str,
    ) -> Workflow:
        """
        Load workflow from the given path under the given module_name.

        :param module_name: Name against which to register the workflow.
        :param path: Path to the directory containing the workflow.

        :return: A Workflow object containing the loaded workflow.
        """
        try:
            # Make sure the module_name is a valid Python identifier
            if not module_name.isidentifier():
                raise ValueError(f"Invalid module name: {module_name}")

            # Load the spec from the path
            p = Path(path)
            if p.is_dir():
                p = p / "__init__.py"

            spec = importlib.util.spec_from_file_location(module_name, p)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load module from {path}")

            # Get the module from the spec
            module = importlib.util.module_from_spec(spec)

            sys.modules[module_name] = module

            # Execute the module
            spec.loader.exec_module(module)

            # Create the Workflow and return it.
            return Workflow(name=module_name, module=module)

        except Exception as ex:
            raise rex.WorkflowLoadException(path) from ex
