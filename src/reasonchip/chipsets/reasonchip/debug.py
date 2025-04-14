# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

"""
# ReasonChip Logging

This module provides simple logging calls to explicity log within the
pipelines. Standard levels are supported.


"""

import typing
import logging

from pydantic import BaseModel, Field

from reasonchip.core.engine.registry import Registry


class LogRequest(BaseModel):
    level: typing.Literal["info", "debug", "warning", "error", "critical"] = (
        Field(description="The log level to set")
    )
    message: typing.Any = Field(
        description="The message to log. It should be able to be converted to a string."
    )


class LogResponse(BaseModel):
    pass


@Registry.register
async def log(request: LogRequest) -> LogResponse:
    """
    Log a message with a specific log level.
    """

    msg = str(request.message)

    if request.level == "info":
        logging.info(msg)
    elif request.level == "debug":
        logging.debug(msg)
    elif request.level == "warning":
        logging.warning(msg)
    elif request.level == "error":
        logging.error(msg)
    elif request.level == "critical":
        logging.critical(msg)

    return LogResponse()
