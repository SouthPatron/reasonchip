# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import uuid
import asyncio
import logging

from ..protocol import SocketPacket
from ..transports import ServerTransport

from .switchboard import Switchboard

log = logging.getLogger(__name__)


class Broker:
    def __init__(
        self,
        client_transports: typing.List[ServerTransport],
        worker_transports: typing.List[ServerTransport],
    ) -> None:
        """
        Initializes the Broker with client and worker transports.

        :param client_transports: List of transports for clients.
        :param worker_transports: List of transports for workers.
        """
        assert client_transports
        assert worker_transports

        # Transports
        self._client_transports: typing.List[ServerTransport] = (
            client_transports
        )
        self._worker_transports: typing.List[ServerTransport] = (
            worker_transports
        )

        # Connections
        self._lock: asyncio.Lock = asyncio.Lock()
        self._connections: typing.Dict[uuid.UUID, ServerTransport] = {}

        # Switchboard
        self._switchboard: Switchboard = Switchboard(
            writer_callback=self.send_packet,
        )

    # --------------------- LIFECYCLE -----------------------------------------

    async def start(self):
        """
        Starts the broker by initializing worker and client managers.
        """
        log.info("Starting broker...")

        assert not self._connections

        # Make sure we have some workers ready
        log.info("Starting worker manager...")
        for t in self._worker_transports:
            rc = await t.start_server(
                new_connection_callback=self._connected,
                read_callback=self._worker_read,
                closed_connection_callback=self._worker_closed,
            )
            if not rc:
                raise ConnectionError("Failed to start worker transport")

        # We are ready for some clients
        log.info("Starting client manager...")
        for t in self._client_transports:
            rc = await t.start_server(
                new_connection_callback=self._connected,
                read_callback=self._client_read,
                closed_connection_callback=self._client_closed,
            )
            if not rc:
                raise ConnectionError("Failed to start client transport")

        log.info("Broker started.")

    async def stop(self) -> bool:
        """
        Stops the broker by shutting down client and worker managers.

        :return: True when the broker has been successfully stopped.
        """
        log.info("Stopping broker...")

        # First we stop all the incoming clients
        log.info("Stopping client manager...")
        for t in self._client_transports:
            await t.stop_server()

        # Then we stop all the workers
        log.info("Stopping worker manager...")
        for t in self._worker_transports:
            await t.stop_server()

        log.info("Broker stopped.")
        return True

    # --------------------- CONTROL -------------------------------------------

    async def _connected(
        self,
        transport: ServerTransport,
        connection_id: uuid.UUID,
    ):
        """
        Manages a new incoming connection.

        :param transport: The transport instance for the connection.
        :param connection_id: Unique identifier for the connection.
        """
        async with self._lock:
            log.info(f"Client connected: id=[{connection_id}]")
            assert connection_id not in self._connections
            self._connections[connection_id] = transport

    # --------------------- CLIENT CONTROL ------------------------------------

    async def _client_read(
        self, connection_id: uuid.UUID, packet: SocketPacket
    ):
        """
        Handles incoming packets from client connections.

        :param connection_id: Unique identifier for the connection.
        :param packet: Incoming packet from the client.
        """
        await self._switchboard.client_payload(
            connection_id=connection_id, packet=packet
        )

    async def _client_closed(self, connection_id: uuid.UUID):
        """
        Handles the closure of a client connection.

        :param connection_id: Unique identifier for the connection to be closed.
        """
        async with self._lock:
            log.info(f"Client closed: id=[{connection_id}]")
            assert connection_id in self._connections

            self._connections.pop(connection_id)

            # Notify the switchboard that the client is gone
            await self._switchboard.eliminate_client(connection_id)

    # --------------------- WORKER CONTROL ------------------------------------

    async def _worker_read(
        self, connection_id: uuid.UUID, packet: SocketPacket
    ):
        """
        Handles incoming packets from worker connections.

        :param connection_id: Unique identifier for the connection.
        :param packet: Incoming packet from the worker.
        """
        await self._switchboard.worker_payload(
            connection_id=connection_id, packet=packet
        )

    async def _worker_closed(self, connection_id: uuid.UUID):
        """
        Handles the closure of a worker connection.

        :param connection_id: Unique identifier for the connection to be closed.
        """
        async with self._lock:
            log.info(f"Worker closed: id=[{connection_id}]")
            assert connection_id in self._connections

            self._connections.pop(connection_id)

            # Notify the switchboard that the worker is gone
            await self._switchboard.eliminate_worker(connection_id)

    # --------------------- SUPPORT METHODS -----------------------------------

    async def send_packet(
        self,
        connection_id: uuid.UUID,
        packet: SocketPacket,
    ) -> bool:
        """
        Sends a packet to a specific connection if it exists.

        :param connection_id: Unique identifier for the connection.
        :param packet: Packet to be sent.

        :return: True if the packet was sent successfully, False otherwise.
        """
        async with self._lock:
            conn = self._connections.get(connection_id)
            if conn is None:
                return False

            return await conn.send_packet(connection_id, packet)
