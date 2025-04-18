# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import uuid
import typing
import enum
import asyncio
import struct
import logging

from pydantic import BaseModel


DEFAULT_LISTENERS = [
    "socket:///tmp/reasonchip-broker-worker.sock",
    "tcp://[::1]/",
    "grpc://[::1]/",
]
DEFAULT_SERVERS = [
    "socket:///tmp/reasonchip-broker-client.sock",
    "tcp://[::1]/",
    "grpc://[::1]/",
    "http://[::1]/",
]

DEFAULT_CLIENT_PORT_TCP = 51500
DEFAULT_CLIENT_PORT_GRPC = 51501
DEFAULT_CLIENT_PORT_HTTP = 51502

DEFAULT_WORKER_PORT_TCP = 51510
DEFAULT_WORKER_PORT_GRPC = 51511


class PacketType(enum.StrEnum):
    """
    The type of packet.
    """

    # Server side operations
    REGISTER = "REGISTER"
    SHUTDOWN = "SHUTDOWN"

    # Engaged operations from clients
    RUN = "RUN"
    CANCEL = "CANCEL"
    RESULT = "RESULT"


class ResultCode(enum.StrEnum):
    """
    The result code for a packet.
    """

    OK = "OK"
    BAD_PACKET = "BAD_PACKET"
    UNSUPPORTED_PACKET_TYPE = "UNSUPPORTED_PACKET_TYPE"
    NO_CAPACITY = "NO_CAPACITY"
    NOT_FOR_US = "NOT_FOR_US"
    COOKIE_NOT_FOUND = "COOKIE_NOT_FOUND"
    COOKIE_COLLISION = "COOKIE_COLLISION"
    WORKER_WENT_AWAY = "WORKER_WENT_AWAY"
    BROKER_WENT_AWAY = "BROKER_WENT_AWAY"
    CANCELLED = "CANCELLED"
    EXCEPTION = "EXCEPTION"


class SocketPacket(BaseModel):
    """
    This is the base class for all packets that are sent between the client
    and the server.
    """

    packet_type: PacketType

    # Common variables
    cookie: typing.Optional[uuid.UUID] = None

    # Register variables
    capacity: typing.Optional[int] = None

    # Run variables
    pipeline: typing.Optional[str] = None
    variables: typing.Optional[str] = None

    # Result variables
    rc: typing.Optional[ResultCode] = None
    error: typing.Optional[str] = None
    stacktrace: typing.Optional[typing.List[str]] = None
    result: typing.Optional[str] = None


async def receive_packet(
    reader: asyncio.StreamReader,
) -> typing.Optional[SocketPacket]:
    """
    Receive a packet from the reader stream.

    In the case of receiving None from this function, the connection should be
    regarded as dead and unrecoverable.

    :param reader: The reader stream.

    :return: The packet received, or None if an error occurred.
    """
    try:
        logging.debug("Waiting to receive packet from stream")

        length_bytes = await reader.readexactly(4)
        length = struct.unpack("!I", length_bytes)[0]

        logging.debug(f"Been told to expect {length} octets")

        msg_bytes = await reader.readexactly(length)
        msg_str = struct.unpack(f"!{length}s", msg_bytes)[0]

        logging.debug(f"Read {length} octets")

        req = SocketPacket.model_validate_json(msg_str.decode("utf-8"))

        logging.debug("Packet received and parsed from stream")

        return req
    except:
        logging.debug("Failed to read packet from stream", exc_info=True)
        return None


async def send_packet(
    writer: asyncio.StreamWriter,
    request: SocketPacket,
) -> bool:
    """
    Send a packet to the writer stream.

    In the case of receiving False from this function, the connection should be
    regarded as dead and unrecoverable.

    :param writer: The writer stream.
    :param request: The packet to send.

    :return: True if the packet was sent successfully, False otherwise.
    """
    try:
        logging.debug("Sending packet to stream")

        msg_str = request.model_dump_json().encode("utf-8")
        length = len(msg_str)

        msg_bytes = struct.pack(f"!{length}s", msg_str)
        length_bytes = struct.pack("!I", length)

        logging.debug(f"Sending {length} octects")

        writer.write(length_bytes + msg_bytes)
        await writer.drain()

        logging.debug("Packet written to stream")
        return True
    except:
        logging.debug("Failed to write packet to stream", exc_info=True)
        return False
