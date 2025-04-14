# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import asyncio
import typing
import uuid
import logging

from dataclasses import dataclass, field

from ..protocol import SocketPacket, PacketType, ResultCode
from ..transports import ClientTransport


@dataclass
class ConnectionInfo:
    connection_id: uuid.UUID
    cookies: typing.List[uuid.UUID] = field(default_factory=list)
    incoming_queue: asyncio.Queue = field(default_factory=asyncio.Queue)


class Multiplexor:

    def __init__(
        self,
        transport: ClientTransport,
    ) -> None:
        self._transport: ClientTransport = transport
        self._dead: asyncio.Event = asyncio.Event()

        self._lock: asyncio.Lock = asyncio.Lock()
        self._connections: typing.Dict[uuid.UUID, ConnectionInfo] = {}
        self._cookies: typing.Dict[uuid.UUID, ConnectionInfo] = {}

    # -------------------------- LIFECYCLE -----------------------------------

    async def start(self) -> bool:
        logging.debug("Starting multiplexor")

        # Clear the event
        self._dead.clear()

        # Start the connection
        rc = await self._transport.connect(callback=self._incoming_callback)
        if rc is False:
            raise ConnectionError("Failed to connect to server")

        logging.debug("Multiplexor started")
        return True

    async def wait(self, timeout: typing.Optional[float] = None) -> bool:
        logging.debug("Waiting for multiplexor to stop")

        # Wait for death
        if not timeout:
            await self._dead.wait()

        else:
            t = asyncio.create_task(self._dead.wait())
            done, _ = await asyncio.wait([t], timeout=timeout)
            if not done:
                logging.debug("Timeout waiting for transport to stop")
                return False

        # Successful exit
        logging.debug("Multiplexor stopped")
        return True

    async def stop(self, timeout: typing.Optional[float] = None) -> bool:
        logging.debug("Stopping multiplexor")

        await self._transport.disconnect()

        return await self.wait(timeout=timeout)

    # -------------------------- REGISTRATION --------------------------------

    async def register(self, connection_id: uuid.UUID) -> ConnectionInfo:
        logging.debug(f"Registering connection: {connection_id}")

        async with self._lock:
            if connection_id in self._connections:
                logging.error(f"Connection already registered: {connection_id}")
                raise ValueError("Client already registered")

            cl = ConnectionInfo(connection_id=connection_id)
            self._connections[connection_id] = cl

            logging.debug(f"Registered connection: {connection_id}")
            return cl

    async def release(self, connection_id: uuid.UUID) -> bool:
        logging.debug(f"Releasing connection: {connection_id}")

        async with self._lock:
            if connection_id not in self._connections:
                logging.debug(f"Connection not found: {connection_id}")
                return False

            logging.debug(f"Released connection: {connection_id}")
            return True

    # -------------------------- SEND & RECV PACKET --------------------------

    async def send_packet(
        self,
        connection_id: uuid.UUID,
        packet: SocketPacket,
    ) -> bool:

        async with self._lock:
            conn = self._connections.get(connection_id, None)
            if not conn:
                logging.warning(f"Connection not found: {connection_id}")
                return False

            cookie = packet.cookie
            assert cookie

            if cookie not in self._cookies:
                self._cookies[cookie] = conn
                conn.cookies.append(cookie)

            return await self._transport.send_packet(packet)

    async def _incoming_callback(
        self, transport_cookie: uuid.UUID, packet: typing.Optional[SocketPacket]
    ):
        # Transport is disconnected. Kill everything.
        if packet is None:
            await self._death_process()
            self._dead.set()
            return

        # Route the packet to the correct connection
        async with self._lock:
            cookie = packet.cookie
            assert cookie

            conn = self._cookies.get(cookie, None)
            if not conn:
                logging.error(f"Received packet with unknown cookie: {cookie}")
                return

            await conn.incoming_queue.put(packet)

            if packet.packet_type == PacketType.RESULT:
                conn.cookies.remove(cookie)
                del self._cookies[cookie]

    # -------------------------- THE DEATH PROCESS ---------------------------

    async def _death_process(self):

        async with self._lock:
            for conn in self._connections.values():
                for cookie in conn.cookies:
                    await conn.incoming_queue.put(
                        SocketPacket(
                            packet_type=PacketType.RESULT,
                            cookie=cookie,
                            rc=ResultCode.BROKER_WENT_AWAY,
                            error="The connection to the broker went away",
                        )
                    )

            self._connections.clear()
            self._cookies.clear()
