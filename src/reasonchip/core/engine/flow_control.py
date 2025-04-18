# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

from __future__ import annotations

import typing

from .pipelines import Task


FlowType = typing.List[Task]


class FlowControl:

    def __init__(self, flow: FlowType):
        """
        Constructor.

        """
        self._flow: FlowType = flow.copy()

    @property
    def flow(self) -> FlowType:
        return self._flow

    def has_next(self) -> bool:
        """
        Returns true if there's another task in the flow.

        :return: True if there's another task in the flow else False
        """
        return len(self._flow) > 0

    def peek(self) -> Task:
        """
        Peeks at the next task in the flow.

        :return: The next task.
        """
        return self._flow[0]

    def pop(self) -> Task:
        """
        Pops the next task from the flow.

        :return: The next task.
        """
        return self._flow.pop(0)
