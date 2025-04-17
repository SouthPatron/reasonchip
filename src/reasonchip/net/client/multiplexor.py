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

log = logging.getLogger(__name__)


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
        """
        Start the multiplexor by connecting the transport and setting it up.

        :return: True if started successfully.
        """
        log.debug("Starting multiplexor")

        # Clear the event
        self._dead.clear()

        # Start the connection
        rc = await self._transport.connect(callback=self._incoming_callback)
        if rc is False:
            raise ConnectionError("Failed to connect to server")

        log.debug("Multiplexor started")
        return True

    async def wait(self, timeout: typing.Optional[float] = None) -> bool:
        """
        Wait for the multiplexor to stop or until the optional timeout.

        :param timeout: Maximum time to wait in seconds, or None to wait indefinitely.
        :return: True if stopped, False if timed out.
        """
        log.debug("Waiting for multiplexor to stop")

        # Wait for death
        if not timeout:
            await self._dead.wait()

        else:
            t = asyncio.create_task(self._dead.wait())
            done, _ = await asyncio.wait([t], timeout=timeout)
            if not done:
                log.debug("Timeout waiting for transport to stop")
                return False

        # Successful exit
        log.debug("Multiplexor stopped")
        return True

    async def stop(self, timeout: typing.Optional[float] = None) -> bool:
        """
        Stop the multiplexor by disconnecting the transport and waiting for shutdown.

        :param timeout: Maximum time to wait for shutdown in seconds, or None.
        :return: True if stopped successfully, False if timed out.
        """
        log.debug("Stopping multiplexor")

        await self._transport.disconnect()

        return await self.wait(timeout=timeout)

    # -------------------------- REGISTRATION --------------------------------

    async def register(self, connection_id: uuid.UUID) -> ConnectionInfo:
        """
        Register a new connection by its unique identifier.

        :param connection_id: The UUID of the connection to register.
        :return: The ConnectionInfo object for the registered connection.
        :raises ValueError: If the connection is already registered.
        """
        log.debug(f"Registering connection: {connection_id}")

        async with self._lock:
            if connection_id in self._connections:
                log.error(f"Connection already registered: {connection_id}")
                raise ValueError("Client already registered")

            cl = ConnectionInfo(connection_id=connection_id)
            self._connections[connection_id] = cl

            log.debug(f"Registered connection: {connection_id}")
            return cl

    async def release(self, connection_id: uuid.UUID) -> bool:
        """
        Release a registered connection, signaling it is no longer active.

        :param connection_id: The UUID of the connection to release.
        :return: True if connection was found and released, False otherwise.
        """
        log.debug(f"Releasing connection: {connection_id}")

        async with self._lock:
            if connection_id not in self._connections:
                log.debug(f"Connection not found: {connection_id}")
                return False

            # Actual removal or cleanup logic is not shown in existing code,
            # so only log release and return True here.
            log.debug(f"Released connection: {connection_id}")
            return True

    # -------------------------- SEND & RECV PACKET --------------------------

    async def send_packet(
        self,
        connection_id: uuid.UUID,
        packet: SocketPacket,
    ) -> bool:
        """
        Send a packet over the transport associated with the given connection.

        :param connection_id: The UUID of the connection to send through.
        :param packet: The SocketPacket to send.
        :return: True on successful send, False if connection not found.
        """

        async with self._lock:
            conn = self._connections.get(connection_id, None)
            if not conn:
                log.warning(f"Connection not found: {connection_id}")
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
        """
        Callback for incoming packets from the transport, routing them to
        the appropriate connection's queue or handling disconnection.

        :param transport_cookie: The cookie identifying the transport packet.
        :param packet: The incoming SocketPacket or None if disconnected.
        """
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
                log.error(f"Received packet with unknown cookie: {cookie}")
                return

            await conn.incoming_queue.put(packet)

            if packet.packet_type == PacketType.RESULT:
                conn.cookies.remove(cookie)
                del self._cookies[cookie]

    # -------------------------- THE DEATH PROCESS ---------------------------

    async def _death_process(self):
        """
        Handle cleanup and notify all connections that the broker has gone away.
        """

        async with self._lock:
            # Notify each connection queue with a error result packet
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
