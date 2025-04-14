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


class Client:

    def __init__(
        self,
        multiplexor: Multiplexor,
        cookie: typing.Optional[uuid.UUID] = None,
    ):
        self._multiplexor: Multiplexor = multiplexor
        self._cookie: uuid.UUID = cookie or uuid.uuid4()
        self._connection: typing.Optional[ConnectionInfo] = None

    async def __aenter__(self):
        logging.debug(f"Creating client with cookie: {self._cookie}")
        self._connection = await self._multiplexor.register(
            connection_id=self._cookie,
        )
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if self._connection:
            await self._multiplexor.release(self._cookie)
            self._connection = None
            logging.debug(f"Client released with cookie: {self._cookie}")

    def get_conn(self) -> ConnectionInfo:
        assert self._connection is not None
        return self._connection

    def get_cookie(self) -> uuid.UUID:
        return self._cookie

    async def send_packet(self, packet: SocketPacket) -> bool:
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

        conn = self.get_conn()

        if timeout:
            t = asyncio.create_task(conn.incoming_queue.get())
            done, _ = await asyncio.wait([t], timeout=timeout)
            if not done:
                return None

            packet = t.result()

        else:
            packet = await conn.incoming_queue.get()

        assert isinstance(packet, SocketPacket)
        return packet
