# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

from __future__ import annotations

import typing

from .. import exceptions as rex

from .workflows import (
    WorkflowContext,
    WorkflowStep,
    WorkflowSet,
)


class EngineContext(WorkflowContext):

    def __init__(
        self,
        workflow_set: WorkflowSet,
    ):
        self._workflow_set: WorkflowSet = workflow_set
        self._stack: typing.List[str] = []

    async def branch(
        self,
        name: str,
        *args,
        **kwargs,
    ) -> typing.Any:

        print(f"Branching to workflow '{name}'")
        fqn: str = self._resolve(name)

        print(f"Resolved workflow name: {fqn}")

        step: WorkflowStep = await self._workflow_set.resolve(fqn)

        self._stack.append(fqn)

        try:
            rc = await step(self, *args, **kwargs)

        except rex.RestartEngineException as e:
            e.name = self._resolve(e.name)
            raise

        finally:
            self._stack.pop()

        return rc

    def _resolve(self, name: str) -> str:
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


class Engine:
    """
    A class with a big name and a little job.
    """

    def __init__(
        self,
        workflow_set: WorkflowSet,
    ):
        """
        Constructor.
        """
        self._workflow_set: WorkflowSet = workflow_set

    @property
    def workflow_set(self) -> WorkflowSet:
        return self._workflow_set

    async def run(
        self,
        context: EngineContext,
        entry: str,
        *args,
        **kwargs,
    ) -> typing.Any:

        t_entry = entry
        t_args = args
        t_kwargs = kwargs

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
                continue

            except rex.TerminateEngineException as e:
                return e.rc
