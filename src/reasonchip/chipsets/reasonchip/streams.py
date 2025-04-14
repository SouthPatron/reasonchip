# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

"""
# ReasonChip Streams

This module provides ReasonChips for handling standard input (stdin),
standard output (stdout), and standard error (stderr) using bytes.
"""

import sys

from pydantic import BaseModel, Field

from reasonchip.core.engine.registry import Registry


class StdinRequest(BaseModel):
    max_bytes: int = Field(
        default=1024,
        description="Maximum number of bytes to read from stdin.",
    )


class StdinResponse(BaseModel):
    data: bytes = Field(
        description="Bytes read from stdin.",
    )


@Registry.register
async def read_stdin(request: StdinRequest) -> StdinResponse:
    """
    Read up to `max_bytes` from stdin as bytes.
    """
    data = sys.stdin.buffer.read(request.max_bytes)
    return StdinResponse(data=data)


class StdoutRequest(BaseModel):
    data: bytes = Field(
        description="Bytes to write to stdout.",
    )


class StdoutResponse(BaseModel):
    success: bool = Field(
        description="Indicates if writing to stdout was successful.",
    )


@Registry.register
async def write_stdout(request: StdoutRequest) -> StdoutResponse:
    """
    Write bytes to stdout.
    """
    try:
        sys.stdout.buffer.write(request.data)
        sys.stdout.buffer.flush()
        return StdoutResponse(success=True)
    except Exception:
        return StdoutResponse(success=False)


class StderrRequest(BaseModel):
    data: bytes = Field(
        description="Bytes to write to stderr.",
    )


class StderrResponse(BaseModel):
    success: bool = Field(
        description="Indicates if writing to stderr was successful.",
    )


@Registry.register
async def write_stderr(request: StderrRequest) -> StderrResponse:
    """
    Write bytes to stderr.
    """
    try:
        sys.stderr.buffer.write(request.data)
        sys.stderr.buffer.flush()
        return StderrResponse(success=True)
    except Exception:
        return StderrResponse(success=False)


class PrintRequest(BaseModel):
    message: str = Field(
        description="The message to print to stdout.",
    )


class PrintResponse(BaseModel):
    success: bool = Field(
        description="Indicates if the print operation was successful.",
    )


@Registry.register
async def print_stdout(request: PrintRequest) -> PrintResponse:
    """
    Print a message to stdout.
    """
    try:
        print(request.message)
        return PrintResponse(success=True)
    except Exception:
        return PrintResponse(success=False)


class ReadRequest(BaseModel):
    max_bytes: int = Field(
        default=1024,
        description="Maximum number of bytes to read from stdin.",
    )


class ReadResponse(BaseModel):
    data: bytes = Field(
        description="Bytes read from stdin.",
    )


@Registry.register
async def read_bytes(request: ReadRequest) -> ReadResponse:
    """
    Read up to `max_bytes` from stdin as bytes.
    """
    data = sys.stdin.buffer.read(request.max_bytes)
    return ReadResponse(data=data)


class ReadlineRequest(BaseModel):
    max_bytes: int = Field(
        default=1024,
        description="Maximum number of bytes to read from stdin in a single line.",
    )


class ReadlineResponse(BaseModel):
    data: bytes = Field(
        description="A single line read from stdin as bytes.",
    )


@Registry.register
async def read_line(request: ReadlineRequest) -> ReadlineResponse:
    """
    Read a single line from stdin as bytes.
    """
    data = sys.stdin.buffer.readline(request.max_bytes)
    return ReadlineResponse(data=data)
