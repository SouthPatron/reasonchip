# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import uuid
import typing
import enum

from pydantic import BaseModel


class PacketType(enum.StrEnum):
    """
    The type of packet.
    """

    RUN = "RUN"
    CANCEL = "CANCEL"


class ResultCode(enum.StrEnum):
    """
    The result code for a packet.
    """

    OK = "OK"
    BAD_PACKET = "BAD_PACKET"
    UNSUPPORTED_PACKET_TYPE = "UNSUPPORTED_PACKET_TYPE"
    COOKIE_NOT_FOUND = "COOKIE_NOT_FOUND"
    COOKIE_COLLISION = "COOKIE_COLLISION"
    EXCEPTION = "EXCEPTION"


class SocketPacket(BaseModel):
    """
    This is the base class for all packets that are sent for processing.
    """

    packet_type: PacketType
    cookie: typing.Optional[uuid.UUID] = None
    workflow: typing.Optional[str] = None
    variables: typing.Optional[str] = None
