# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

"""
# String utility functions

"""

import typing
import time

from pydantic import BaseModel, Field

from reasonchip.core.engine.registry import Registry


class SleepRequest(BaseModel):
    """
    Request structure.
    """

    milliseconds: int


class SleepResponse(BaseModel):
    """
    Response structure.
    """

    status: typing.Literal[
        "OK",
        "ERROR",
    ] = Field(description="Status of the request.")


@Registry.register
async def sleep(request: SleepRequest) -> SleepResponse:

    if request.milliseconds <= 0:
        return SleepResponse(status="ERROR")

    time.sleep(request.milliseconds / 1000)

    return SleepResponse(status="OK")
