#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import asyncio
import os
import typing
import uuid
import logging

from dataclasses import dataclass, field

from ..protocol import SocketPacket, receive_packet, send_packet

from .server_transport import (
    ServerTransport,
    NewConnectionCallbackType,
    ReadCallbackType,
    ClosedConnectionCallbackType,
)

log = logging.getLogger(__name__)


@dataclass
class ClientConnection:
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    death_signal: asyncio.Event = field(default_factory=asyncio.Event)
    connection_id: uuid.UUID = field(default_factory=uuid.uuid4)
    outgoing_queue: asyncio.Queue = field(default_factory=asyncio.Queue)


class SocketServer(ServerTransport):

    def __init__(
        self,
        path=None,
        limit=2**16,
        sock=None,
        backlog=100,
        ssl=None,
        ssl_handshake_timeout=None,
        ssl_shutdown_timeout=None,
    ):
        """
        Initialize a new SocketServer instance.

        :param path: The filesystem path for the UNIX socket.
        :param limit: The buffer size limit for the stream reader.
        :param sock: Existing socket to use.
        :param backlog: The maximum number of queued connections.
        :param ssl: SSL context if SSL is required.
        :param ssl_handshake_timeout: Timeout for SSL handshake.
        :param ssl_shutdown_timeout: Timeout for SSL shutdown.
        """
        super().__init__()

        # Parameters
        self._path = path
        self._limit = limit
        self._sock = sock
        self._backlog = backlog
        self._ssl = ssl
        self._ssl_handshake_timeout = ssl_handshake_timeout
        self._ssl_shutdown_timeout = ssl_shutdown_timeout

        # Callbacks
        self._new_connection_callback: typing.Optional[
            NewConnectionCallbackType
        ] = None
        self._read_callback: typing.Optional[ReadCallbackType] = None
        self._closed_connection_callback: typing.Optional[
            ClosedConnectionCallbackType
        ] = None

        # Server state
        self._lock: asyncio.Lock = asyncio.Lock()
        self._server: typing.Optional[asyncio.Server] = None
        self._connections: typing.Dict[uuid.UUID, ClientConnection] = {}

    async def start_server(
        self,
        new_connection_callback: NewConnectionCallbackType,
        read_callback: ReadCallbackType,
        closed_connection_callback: ClosedConnectionCallbackType,
    ) -> bool:
        """
        Start the UNIX socket server and register the callbacks.

        :param new_connection_callback: Called when a new connection is established.
        :param read_callback: Called when a packet is read from a connection.
        :param closed_connection_callback: Called when a connection is closed.

        :return: True if the server started successfully.
        """

        if self._path and os.path.exists(self._path):
            # Remove any existing socket file to avoid conflict
            log.debug(f"Removing existing socket {self._path}")
            os.remove(self._path)

        self._new_connection_callback = new_connection_callback
        self._read_callback = read_callback
        self._closed_connection_callback = closed_connection_callback

        self._server = await asyncio.start_unix_server(
            self._connection,
            path=self._path,
            limit=self._limit,
            sock=self._sock,
            backlog=self._backlog,
            ssl=self._ssl,
            ssl_handshake_timeout=self._ssl_handshake_timeout,
            ssl_shutdown_timeout=self._ssl_shutdown_timeout,
        )

        log.info(f"Socket server started on {self._path}")

        return True

    async def stop_server(self) -> bool:
        """
        Stop the server and signal all active connections to close.

        :return: True if stop signal sent successfully.
        """
        async with self._lock:
            # Signal all connections to close
            for conn in self._connections.values():
                conn.death_signal.set()

        log.info("Stop server: Signaled all connections to close")

        return True

    async def send_packet(
        self,
        connection_id: uuid.UUID,
        packet: SocketPacket,
    ) -> bool:
        """
        Enqueue a packet to be sent on a specific connection.

        :param connection_id: UUID of the client connection.
        :param packet: Packet to send.

        :return: True if the packet was queued successfully, False if connection not found.
        """

        async with self._lock:
            conn = self._connections.get(connection_id, None)
            if conn is None:
                log.warning(
                    f"Attempt to send to non-existent connection {connection_id}"
                )
                return False

            # Put the packet in the outgoing queue
            await conn.outgoing_queue.put(packet)
            log.debug(f"Packet queued for connection {connection_id}")
            return True

    async def close_connection(
        self,
        connection_id: uuid.UUID,
    ) -> bool:
        """
        Close a specific client connection.

        :param connection_id: UUID of the client connection to close.

        :return: True if the connection was signaled to close, False if not found.
        """
        async with self._lock:
            conn = self._connections.get(connection_id, None)
            if conn is None:
                log.warning(
                    f"Attempt to close non-existent connection {connection_id}"
                )
                return False

            # Set the death signal to close connection
            conn.death_signal.set()
            log.info(f"Signaled connection {connection_id} to close")
            return True

    # ------------------------------------------------------------------------

    async def _connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """
        Internal handler for new client connections.

        :param reader: StreamReader for incoming data.
        :param writer: StreamWriter for outgoing data.
        """
        assert self._new_connection_callback is not None
        assert self._closed_connection_callback is not None

        conn = ClientConnection(
            reader=reader,
            writer=writer,
        )

        # Register the connection
        async with self._lock:
            self._connections[conn.connection_id] = conn
            log.info(f"New connection established: {conn.connection_id}")
            await self._new_connection_callback(self, conn.connection_id)

        # handle all incoming and outgoing packets for this client connection
        await self._client_loop(conn)

        # Remove the connection from the list of connections
        async with self._lock:
            self._connections.pop(conn.connection_id, None)
            log.info(f"Connection closed: {conn.connection_id}")
            await self._closed_connection_callback(conn.connection_id)

        # Close the writer cleanly
        writer.close()
        await writer.wait_closed()

    async def _client_loop(self, conn: ClientConnection) -> None:
        """
        Handle the communication loop with a client connection.

        :param conn: The client connection instance.
        """
        assert self._read_callback is not None

        # Create async tasks for death signal, reading and writing
        t_die = asyncio.create_task(conn.death_signal.wait())
        t_read = asyncio.create_task(receive_packet(conn.reader))
        t_write = asyncio.create_task(conn.outgoing_queue.get())

        wl = [t_die, t_read, t_write]

        while wl:
            done, _ = await asyncio.wait(
                wl,
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Read a packet
            if t_read in done:
                assert t_read and t_read.done()
                wl.remove(t_read)

                if not t_read.cancelled():
                    packet = t_read.result()
                    assert packet is None or isinstance(packet, SocketPacket)

                    if packet is None:
                        # Connection closed remotely, initiate cleanup
                        if t_write:
                            t_write.cancel()
                        if t_die:
                            conn.death_signal.set()
                        log.info(
                            f"Connection {conn.connection_id} closed by peer"
                        )

                    else:
                        # Pass received packet to read callback
                        await self._read_callback(conn.connection_id, packet)

                        # Prepare to read next packet
                        t_read = asyncio.create_task(
                            receive_packet(conn.reader)
                        )
                        wl.append(t_read)

                else:
                    t_read = None

            # Write a packet
            if t_write in done:
                assert t_write and t_write.done()
                wl.remove(t_write)

                if not t_write.cancelled():
                    packet = t_write.result()
                    assert isinstance(packet, SocketPacket)

                    # Send packet to client
                    await send_packet(conn.writer, packet)
                    log.debug(f"Sent packet to connection {conn.connection_id}")

                    # Prepare to wait for next outgoing packet
                    t_write = asyncio.create_task(conn.outgoing_queue.get())
                    wl.append(t_write)

                else:
                    t_write = None

            # Die
            if t_die in done:
                assert t_die and t_die.done()
                wl.remove(t_die)
                conn.death_signal.set()

                if t_read:
                    t_read.cancel()

                if t_write:
                    t_write.cancel()

                log.info(
                    f"Connection {conn.connection_id} death signal received, shutting down client loop"
                )
