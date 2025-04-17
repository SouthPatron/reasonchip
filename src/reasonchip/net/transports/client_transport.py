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

ReadCallbackType = typing.Callable[
    [uuid.UUID, typing.Optional[SocketPacket]], typing.Awaitable[None]
]


class ClientTransport(ABC):

    @abstractmethod
    async def connect(
        self,
        callback: ReadCallbackType,
        cookie: typing.Optional[uuid.UUID] = None,
    ) -> bool:
        """
        Connect to the client transport and set the read callback.

        :param callback: The callback to invoke on read events.
        :param cookie: Optional UUID for tracking the connection.

        :return: True if connection succeeds, False otherwise.
        """

    @abstractmethod
    async def disconnect(self):
        """
        Disconnect the client transport.
        """

    @abstractmethod
    async def send_packet(self, packet: SocketPacket) -> bool:
        """
        Send a packet through the client transport.

        :param packet: The SocketPacket to send.

        :return: True if send succeeds, False otherwise.
        """
