# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import uuid
import logging
import asyncio

from ..protocol import SocketPacket

from .multiplexor import Multiplexor, ConnectionInfo

log = logging.getLogger(__name__)


class Client:

    def __init__(
        self,
        multiplexor: Multiplexor,
        cookie: typing.Optional[uuid.UUID] = None,
    ):
        """
        Create a new Client instance.

        :param multiplexor: The Multiplexor managing connections
        :param cookie: Optional unique identifier for the client
        """
        self._multiplexor: Multiplexor = multiplexor
        self._cookie: uuid.UUID = cookie or uuid.uuid4()
        self._connection: typing.Optional[ConnectionInfo] = None

    async def __aenter__(self):
        """
        Async context manager entry, registers the client connection.

        :return: self
        """
        log.debug(f"Creating client with cookie: {self._cookie}")
        self._connection = await self._multiplexor.register(
            connection_id=self._cookie,
        )
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """
        Async context manager exit, releases client connection.

        :param exc_type: Exception type if any
        :param exc_value: Exception value if any
        :param traceback: Traceback if any
        """
        if self._connection:
            await self._multiplexor.release(self._cookie)
            self._connection = None
            log.debug(f"Client released with cookie: {self._cookie}")

    def get_conn(self) -> ConnectionInfo:
        """
        Get the current ConnectionInfo object for this client.

        :return: Current ConnectionInfo
        """
        assert self._connection is not None
        return self._connection

    def get_cookie(self) -> uuid.UUID:
        """
        Get the client's unique cookie identifier.

        :return: UUID cookie
        """
        return self._cookie

    async def send_packet(self, packet: SocketPacket) -> bool:
        """
        Send a packet via the multiplexor connection.

        :param packet: Packet to be sent
        :return: True if send succeeded, False otherwise
        """
        conn = self.get_conn()
        packet.cookie = conn.connection_id
        return await self._multiplexor.send_packet(
            conn.connection_id,
            packet,
        )

    async def receive_packet(
        self,
        timeout: typing.Optional[float] = None,
    ) -> typing.Optional[SocketPacket]:
        """
        Receive a packet from the multiplexor connection.

        :param timeout: Optional timeout in seconds
        :return: Received SocketPacket or None if timed out
        """

        conn = self.get_conn()

        if timeout:
            # Wait for packet with timeout
            t = asyncio.create_task(conn.incoming_queue.get())
            done, _ = await asyncio.wait([t], timeout=timeout)
            if not done:
                return None

            packet = t.result()

        else:
            packet = await conn.incoming_queue.get()

        assert isinstance(packet, SocketPacket)
        return packet
