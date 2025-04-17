# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import uuid
import logging

from abc import ABC, abstractmethod

from ..protocol import SocketPacket

log = logging.getLogger(__name__)

NewConnectionCallbackType = typing.Callable[
    ["ServerTransport", uuid.UUID], typing.Awaitable[None]
]
ReadCallbackType = typing.Callable[
    [uuid.UUID, SocketPacket], typing.Awaitable[None]
]
ClosedConnectionCallbackType = typing.Callable[
    [uuid.UUID], typing.Awaitable[None]
]


class ServerTransport(ABC):

    @abstractmethod
    async def start_server(
        self,
        new_connection_callback: NewConnectionCallbackType,
        read_callback: ReadCallbackType,
        closed_connection_callback: ClosedConnectionCallbackType,
    ) -> bool:
        """
        Starts the server transport and sets up the callbacks for connection events.

        :param new_connection_callback: Coroutine called when a new connection is established.
        :param read_callback: Coroutine called when a packet is read from a connection.
        :param closed_connection_callback: Coroutine called when a connection is closed.

        :return: True if the server started successfully, False otherwise.
        """
        ...

    @abstractmethod
    async def stop_server(self) -> bool:
        """
        Stops the server transport.

        :return: True if the server stopped successfully, False otherwise.
        """
        ...

    @abstractmethod
    async def send_packet(
        self,
        connection_id: uuid.UUID,
        packet: SocketPacket,
    ) -> bool:
        """
        Sends a packet to the specified connection.

        :param connection_id: The ID of the connection to send the packet to.
        :param packet: The packet to send.

        :return: True if the packet was sent successfully, False otherwise.
        """
        ...

    @abstractmethod
    async def close_connection(
        self,
        connection_id: uuid.UUID,
    ) -> bool:
        """
        Closes the specified connection.

        :param connection_id: The ID of the connection to close.

        :return: True if the connection was closed successfully, False otherwise.
        """
        ...
