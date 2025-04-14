# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import asyncio
import typing
import uuid
import socket

from dataclasses import dataclass, field

from ..protocol import SocketPacket, receive_packet, send_packet

from .server_transport import (
    ServerTransport,
    NewConnectionCallbackType,
    ReadCallbackType,
    ClosedConnectionCallbackType,
)


@dataclass
class ClientConnection:
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    death_signal: asyncio.Event = field(default_factory=asyncio.Event)
    connection_id: uuid.UUID = field(default_factory=uuid.uuid4)
    outgoing_queue: asyncio.Queue = field(default_factory=asyncio.Queue)


class TcpServer(ServerTransport):

    def __init__(
        self,
        hosts=None,
        port=None,
        limit=2**16,
        family=socket.AF_UNSPEC,
        flags=socket.AI_PASSIVE,
        sock=None,
        backlog=100,
        ssl=None,
        reuse_address=None,
        reuse_port=None,
        ssl_handshake_timeout=None,
        ssl_shutdown_timeout=None,
    ):
        super().__init__()

        # Parameters
        self._hosts = hosts
        self._port = port
        self._limit = limit
        self._family = family
        self._flags = flags
        self._sock = sock
        self._backlog = backlog
        self._ssl = ssl
        self._reuse_address = reuse_address
        self._reuse_port = reuse_port
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

        self._new_connection_callback = new_connection_callback
        self._read_callback = read_callback
        self._closed_connection_callback = closed_connection_callback

        self._server = await asyncio.start_server(
            self._connection,
            host=self._hosts,
            port=self._port,
            limit=self._limit,
            family=self._family,
            flags=self._flags,
            sock=self._sock,
            backlog=self._backlog,
            ssl=self._ssl,
            reuse_address=self._reuse_address,
            reuse_port=self._reuse_port,
            ssl_handshake_timeout=self._ssl_handshake_timeout,
            ssl_shutdown_timeout=self._ssl_shutdown_timeout,
        )

        return True

    async def stop_server(self) -> bool:
        async with self._lock:
            for conn in self._connections.values():
                conn.death_signal.set()

        return True

    async def send_packet(
        self,
        connection_id: uuid.UUID,
        packet: SocketPacket,
    ) -> bool:

        async with self._lock:
            conn = self._connections.get(connection_id, None)
            if conn is None:
                return False

            # Put the packet in the outgoing queue
            await conn.outgoing_queue.put(packet)
            return True

    async def close_connection(
        self,
        connection_id: uuid.UUID,
    ) -> bool:
        async with self._lock:
            conn = self._connections.get(connection_id, None)
            if conn is None:
                return False

            # Set the death signal
            conn.death_signal.set()
            return True

    # ------------------------------------------------------------------------

    async def _connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        assert self._new_connection_callback is not None
        assert self._closed_connection_callback is not None

        conn = ClientConnection(
            reader=reader,
            writer=writer,
        )

        # Register the connection
        async with self._lock:
            self._connections[conn.connection_id] = conn
            await self._new_connection_callback(self, conn.connection_id)

        # handle all incoming...
        await self._client_loop(conn)

        # Remove the connection from the list of connections
        async with self._lock:
            self._connections.pop(conn.connection_id, None)
            await self._closed_connection_callback(conn.connection_id)

        # Close the writer cleanly
        writer.close()
        await writer.wait_closed()

    async def _client_loop(self, conn: ClientConnection) -> None:
        assert self._read_callback is not None

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
                        if t_write:
                            t_write.cancel()
                        if t_die:
                            conn.death_signal.set()

                    else:
                        await self._read_callback(conn.connection_id, packet)

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

                    await send_packet(conn.writer, packet)

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
