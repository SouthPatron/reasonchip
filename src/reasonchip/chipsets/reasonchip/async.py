# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

"""
# ReasonChip Async Handling

This module provides async capabilities for ReasonChip.

"""

import asyncio
import typing

from pydantic import BaseModel, Field

from reasonchip.core.engine.registry import Registry


class WaitForRequest(BaseModel):
    task: asyncio.Task = Field(
        description="Task to wait for.",
    )
    timeout: typing.Optional[float] = Field(
        default=None,
        description="Amount of time to wait for the task to complete.",
    )

    class Config:
        arbitrary_types_allowed = True


class WaitForResponse(BaseModel):
    status: typing.Literal[
        "OK",
        "TIMEOUT",
    ] = Field(
        title="Status of the wait operation.",
    )
    resp: typing.Optional[BaseModel] = Field(
        default=None,
        title="The respondList of tasks that were gathered",
    )


@Registry.register
async def wait_for(request: WaitForRequest) -> WaitForResponse:
    """
    Wait for a task to complete.
    """
    try:
        resp = await asyncio.wait_for(
            request.task,
            timeout=request.timeout,
        )
        return WaitForResponse(status="OK", resp=resp)
    except TimeoutError:
        return WaitForResponse(status="TIMEOUT", resp=None)
