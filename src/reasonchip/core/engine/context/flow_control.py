# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

from __future__ import annotations

import typing
import logging

from ..pipelines import Task

log = logging.getLogger(__name__)

FlowType = typing.List[Task]


class FlowControl:

    def __init__(self, flow: FlowType):
        """
        Initialize FlowControl with a list of tasks.

        :param flow: List of tasks representing the flow.
        """
        self._flow: FlowType = flow.copy()
        log.debug(f"Initialized FlowControl with {len(self._flow)} tasks")

    @property
    def flow(self) -> FlowType:
        """
        Returns the current flow list.

        :return: The list of tasks in the flow.
        """
        return self._flow

    def has_next(self) -> bool:
        """
        Returns true if there's another task in the flow.

        :return: True if there's another task in the flow else False
        """
        has_next_value = len(self._flow) > 0
        log.debug(f"Checking has_next: {has_next_value}")
        return has_next_value

    def peek(self) -> Task:
        """
        Peeks at the next task in the flow without removing it.

        :return: The next task.
        """
        next_task = self._flow[0]
        log.debug(f"Peeking task: {next_task}")
        return next_task

    def pop(self) -> Task:
        """
        Pops the next task from the flow.

        :return: The next task.
        """
        next_task = self._flow.pop(0)
        log.debug(f"Popped task: {next_task}")
        return next_task
