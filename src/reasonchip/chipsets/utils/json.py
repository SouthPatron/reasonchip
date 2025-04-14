# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

"""
# JSON Command Chipset

"""

import typing
import json

from pydantic import BaseModel, Field

from reasonchip.core.engine.registry import Registry


class JsonDumpsRequest(BaseModel):
    """
    Request structure.
    """

    obj: typing.Any


class JsonDumpsResponse(BaseModel):
    """
    Response structure.
    """

    status: typing.Literal[
        "OK",
        "ERROR",
    ] = Field(description="Status of the request.")

    result: typing.Optional[str] = Field(
        default=None,
        description="The result of the json dumps (if successful).",
    )
    error_message: typing.Optional[str] = Field(
        default=None, description="Error message if the command failed."
    )


@Registry.register
async def dumps(request: JsonDumpsRequest) -> JsonDumpsResponse:
    """
    Dumps an object to a JSON string.
    """

    try:
        rc = json.dumps(request.obj)
        return JsonDumpsResponse(
            status="OK",
            result=rc,
        )

    except Exception as e:
        return JsonDumpsResponse(
            status="ERROR",
            error_message=str(e),
        )


class JsonLoadsRequest(BaseModel):
    """
    Request structure.
    """

    string: str


class JsonLoadsResponse(BaseModel):
    """
    Response structure.
    """

    status: typing.Literal[
        "OK",
        "ERROR",
    ] = Field(description="Status of the request.")

    result: typing.Optional[typing.Any] = Field(
        default=None,
        description="The result of the json loads (if successful).",
    )
    error_message: typing.Optional[str] = Field(
        default=None, description="Error message if the command failed."
    )


@Registry.register
async def loads(request: JsonLoadsRequest) -> JsonLoadsResponse:
    """
    Loads a JSON string to an object.
    """

    try:
        rc = json.loads(request.string)
        return JsonLoadsResponse(
            status="OK",
            result=rc,
        )

    except Exception as e:
        return JsonLoadsResponse(
            status="ERROR",
            error_message=str(e),
        )
