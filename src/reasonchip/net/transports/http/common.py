# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import logging
import typing
import asyncio
import uuid

from dataclasses import dataclass, field

from ...protocol import SocketPacket, PacketType

log = logging.getLogger(__name__)


@dataclass
class ClientSession:
    """
    Represents a client session with a unique connection ID, an event to signal
    session termination, and a queue for outgoing packets.

    :param connection_id: Unique identifier for the client connection.
    :param death_signal: Event to signal when the session should end.
    :param outgoing_queue: Queue of outgoing SocketPacket objects to be sent.
    """

    connection_id: uuid.UUID = field(default_factory=uuid.uuid4)
    death_signal: asyncio.Event = field(default_factory=asyncio.Event)
    outgoing_queue: asyncio.Queue[SocketPacket] = field(
        default_factory=asyncio.Queue
    )


NewConnectionType = typing.Callable[[ClientSession], typing.Awaitable[None]]
ReadCallback = typing.Callable[
    [ClientSession, SocketPacket], typing.Awaitable[None]
]
DisconnectCallback = typing.Callable[[ClientSession], typing.Awaitable[None]]


@dataclass
class CallbackHooks:
    """
    Container for callback hooks to manage client connection lifecycle events.

    :param new_connection: Callback triggered when a new connection is established.
    :param read_callback: Callback triggered when a packet is read from a client.
    :param disconnect_callback: Callback triggered when a client disconnects.
    """

    new_connection: NewConnectionType
    read_callback: ReadCallback
    disconnect_callback: DisconnectCallback
