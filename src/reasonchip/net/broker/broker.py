import typing
import uuid
import asyncio
import logging

from ..protocol import SocketPacket
from ..transports import ServerTransport

from .switchboard import Switchboard


class Broker:


    def __init__(
        self,
        client_transports: typing.List[ServerTransport],
        worker_transports: typing.List[ServerTransport],
    ) -> None:
        assert client_transports
        assert worker_transports

        # Transports
        self._client_transports: typing.List[ServerTransport] = client_transports
        self._worker_transports: typing.List[ServerTransport] = worker_transports

        # Connections
        self._lock: asyncio.Lock = asyncio.Lock()
        self._connections: typing.Dict[uuid.UUID, ServerTransport] = {}

        # Switchboard
        self._switchboard: Switchboard = Switchboard(
            writer_callback = self.send_packet,
        )


    # --------------------- LIFECYCLE -----------------------------------------


    async def start(self):
        logging.info("Starting broker...")

        assert not self._connections

        # Make sure we have some workers ready
        logging.info("Starting worker manager...")
        for t in self._worker_transports:
            rc = await t.start_server(
                new_connection_callback = self._connected,
                read_callback = self._worker_read,
                closed_connection_callback = self._worker_closed,
            )
            if not rc:
                raise ConnectionError("Failed to start worker transport")

        # We are ready for some clients
        logging.info("Starting client manager...")
        for t in self._client_transports:
            rc = await t.start_server(
                new_connection_callback = self._connected,
                read_callback = self._client_read,
                closed_connection_callback = self._client_closed,
            )
            if not rc:
                raise ConnectionError("Failed to start client transport")

        logging.info("Broker started.")


    async def stop(self) -> bool:
        logging.info("Stopping broker...")

        # First we stop all the incoming clients
        logging.info("Stopping client manager...")
        for t in self._client_transports:
            await t.stop_server()

        # Then we stop all the workers
        logging.info("Stopping worker manager...")
        for t in self._worker_transports:
            await t.stop_server()

        logging.info("Broker stopped.")
        return True



    # --------------------- CONTROL -------------------------------------------

    async def _connected(
        self,
        transport: ServerTransport,
        connection_id: uuid.UUID,
    ):
        async with self._lock:
            logging.info(f"Client connected: id=[{connection_id}]")
            assert connection_id not in self._connections
            self._connections[connection_id] = transport


    # --------------------- CLIENT CONTROL ------------------------------------

    async def _client_read(self, connection_id: uuid.UUID, packet: SocketPacket):
        await self._switchboard.client_payload(
            connection_id = connection_id,
            packet = packet
        )


    async def _client_closed(self, connection_id: uuid.UUID):
        async with self._lock:
            logging.info(f"Client closed: id=[{connection_id}]")
            assert connection_id in self._connections

            self._connections.pop(connection_id)

            # Notify the switchboard that the client is gone
            await self._switchboard.eliminate_client(connection_id)


    # --------------------- WORKER CONTROL ------------------------------------

    async def _worker_read(self, connection_id: uuid.UUID, packet: SocketPacket):
        await self._switchboard.worker_payload(
            connection_id = connection_id,
            packet = packet
        )


    async def _worker_closed(self, connection_id: uuid.UUID):
        async with self._lock:
            logging.info(f"Worker closed: id=[{connection_id}]")
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

        async with self._lock:
            conn = self._connections.get(connection_id)
            if conn is None:
                return False

            return await conn.send_packet(connection_id, packet)

