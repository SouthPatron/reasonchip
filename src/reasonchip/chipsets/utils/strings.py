# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

"""
# String utility functions

"""

import typing
import re

from pydantic import BaseModel, Field

from reasonchip.core.engine.registry import Registry


class RemoveCodeBlockRequest(BaseModel):
    """
    Request structure.
    """

    string: str


class RemoveCodeBlockResponse(BaseModel):
    """
    Response structure.
    """

    status: typing.Literal[
        "OK",
        "ERROR",
    ] = Field(description="Status of the request.")

    language: typing.Optional[str] = Field(
        default=None, description="The language of the code block, if specified"
    )

    result: typing.Optional[str] = Field(
        default=None,
        description="The contents of the string without a code block.",
    )
    error_message: typing.Optional[str] = Field(
        default=None, description="Error message if the command failed."
    )


@Registry.register
async def remove_code_block(
    request: RemoveCodeBlockRequest,
) -> RemoveCodeBlockResponse:
    """
    Removes a fenced code block (triple backticks) and its language specifier
    if present.

    Returns the cleaned text and the detected language (or None if no language
    was found).
    """

    try:
        text = request.string

        pattern = re.compile(r"```(\w+)?\n(.*?)(\n)?```", re.DOTALL)

        match = re.search(pattern, text)

        if match:
            language = match.group(1)
            cleaned_text = text[: match.start()] + text[match.end() :]
        else:
            language = None
            cleaned_text = text

        return RemoveCodeBlockResponse(
            status="OK",
            language=language,
            result=cleaned_text,
        )

    except Exception as e:
        return RemoveCodeBlockResponse(
            status="ERROR",
            error_message=str(e),
        )
