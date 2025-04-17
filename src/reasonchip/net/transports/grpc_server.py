# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import asyncio
import logging
import uuid
import typing
import grpc

from dataclasses import dataclass

from ..protocol import SocketPacket

from .grpc_stubs.reasonchip_pb2 import ReasonChipPacket  # type: ignore
from .grpc_stubs.reasonchip_pb2_grpc import (
    ReasonChipServiceServicer,
    add_ReasonChipServiceServicer_to_server,
)

from .server_transport import (
    ServerTransport,
    NewConnectionCallbackType,
    ReadCallbackType,
    ClosedConnectionCallbackType,
)

from .ssl_options import SSLServerOptions

log = logging.getLogger(__name__)


@dataclass
class ClientSession:
    connection_id: uuid.UUID = uuid.uuid4()
    death_signal: asyncio.Event = asyncio.Event()
    outgoing_queue: asyncio.Queue[SocketPacket] = asyncio.Queue()


class ReasonChipServiceImpl(ReasonChipServiceServicer):
    """
    NOTE: This class is friendly with GrpcServer (It touches privates)
    """

    def __init__(self, server: "GrpcServer"):
        self.server = server

    async def EstablishConnection(self, request_iterator, context):
        """
        gRPC bi-directional streaming method for establishing a client connection.

        This method handles incoming streams of packets from clients and yields
        outgoing packets back to clients. It manages connection lifecycle and
        calls registered callbacks.

        :param request_iterator: An async iterator of incoming ReasonChipPacket messages.
        :param context: The gRPC ServicerContext.

        :return: An async generator yielding ReasonChipPacket messages to the client.
        """
        session = ClientSession()
        connection_id = session.connection_id

        # Register new connection
        async with self.server._lock:
            self.server._connections[connection_id] = session
            if self.server._new_connection_callback:
                await self.server._new_connection_callback(
                    self.server, connection_id
                )

        # Stream reading and writing tasks
        async def reader():
            try:
                async for packet in request_iterator:
                    if self.server._read_callback:

                        # Convert gRPC packet to SocketPacket
                        pkt = SocketPacket(
                            packet_type=packet.packet_type,
                            cookie=packet.cookie,
                            capacity=packet.capacity,
                            pipeline=packet.pipeline,
                            variables=packet.variables,
                            rc=packet.rc,
                            error=packet.error,
                            stacktrace=packet.stacktrace,
                            result=packet.result,
                        )

                        # Invoke the read callback with the received packet
                        await self.server._read_callback(connection_id, pkt)

            except Exception as e:
                log.warning(f"Connection {connection_id} reader error: {e}")
            finally:
                session.death_signal.set()

        try:
            # Create async tasks for reading, writing and connection termination
            t_read = asyncio.create_task(reader())
            t_write = asyncio.create_task(session.outgoing_queue.get())
            t_die = asyncio.create_task(session.death_signal.wait())

            wl = [t_read, t_write, t_die]

            # Loop while there are tasks to wait for
            while wl:
                done, _ = await asyncio.wait(
                    wl,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if t_read in done:
                    wl.remove(t_read)
                    t_read = None

                if t_write in done:
                    assert t_write and t_write.done()
                    wl.remove(t_write)

                    if not t_write.cancelled():
                        packet = t_write.result()
                        assert isinstance(packet, SocketPacket)

                        # Convert SocketPacket to gRPC packet for sending
                        grpc_packet = ReasonChipPacket(
                            packet_type=packet.packet_type,
                            cookie=packet.cookie,
                            capacity=packet.capacity,
                            pipeline=packet.pipeline,
                            variables=packet.variables,
                            rc=packet.rc,
                            error=packet.error,
                            stacktrace=packet.stacktrace,
                            result=packet.result,
                        )
                        # Yield the packet to client
                        yield grpc_packet

                        # Restart write task fetching next packet
                        t_write = asyncio.create_task(
                            session.outgoing_queue.get()
                        )
                        wl.append(t_write)

                    else:
                        t_write = None

                if t_die in done:
                    wl.remove(t_die)

                    # Cancel reader and writer tasks if still active
                    if t_read:
                        t_read.cancel()

                    if t_write:
                        t_write.cancel()

        finally:
            # Cleanup: remove connection and notify closed connection callback
            async with self.server._lock:
                self.server._connections.pop(connection_id, None)
                if self.server._closed_connection_callback:
                    await self.server._closed_connection_callback(connection_id)


class GrpcServer(ServerTransport):

    def __init__(
        self,
        host: typing.Optional[str],
        ssl_options: typing.Optional[SSLServerOptions] = None,
    ):
        """
        Initialize the gRPC server transport.

        :param host: The host address to bind the gRPC server to.
        :param ssl_options: Optional SSL options for secure connections.
        """
        super().__init__()

        self._host = host or "[::]"

        # Connection management
        self._lock: asyncio.Lock = asyncio.Lock()
        self._connections: typing.Dict[uuid.UUID, ClientSession] = {}

        # Callbacks
        self._new_connection_callback: typing.Optional[
            NewConnectionCallbackType
        ] = None
        self._read_callback: typing.Optional[ReadCallbackType] = None
        self._closed_connection_callback: typing.Optional[
            ClosedConnectionCallbackType
        ] = None

        # gRPC server initialization
        self._server = grpc.aio.server()
        self._servicer = ReasonChipServiceImpl(self)

        add_ReasonChipServiceServicer_to_server(self._servicer, self._server)

        if ssl_options:
            creds = self.create_grpc_server_credentials(ssl_options)
            self._server.add_secure_port(self._host, creds)

        else:
            self._server.add_insecure_port(self._host)

    async def start_server(
        self,
        new_connection_callback: NewConnectionCallbackType,
        read_callback: ReadCallbackType,
        closed_connection_callback: ClosedConnectionCallbackType,
    ) -> bool:
        """
        Start the gRPC server and set connection callbacks.

        :param new_connection_callback: Called when a new connection is established.
        :param read_callback: Called when a packet is read from a connection.
        :param closed_connection_callback: Called when a connection is closed.

        :return: True if server started successfully.
        """

        self._new_connection_callback = new_connection_callback
        self._read_callback = read_callback
        self._closed_connection_callback = closed_connection_callback

        await self._server.start()

        log.info(f"gRPC server listening on {self._host}")
        return True

    async def stop_server(self) -> bool:
        """
        Stop the gRPC server.

        :return: True when the server stopped successfully.
        """
        await self._server.stop(0)
        log.info("gRPC server stopped")
        return True

    async def send_packet(
        self,
        connection_id: uuid.UUID,
        packet: SocketPacket,
    ) -> bool:
        """
        Send a packet to a specific client identified by connection_id.

        :param connection_id: The unique ID of the client connection.
        :param packet: The packet to send.

        :return: True if the packet was queued successfully, False if connection not found.
        """
        async with self._lock:
            if session := self._connections.get(connection_id):
                await session.outgoing_queue.put(packet)
                return True

            return False

    async def close_connection(self, connection_id: uuid.UUID) -> bool:
        """
        Close a client connection by setting its death signal.

        :param connection_id: The unique ID of the client connection to close.

        :return: True if the connection was found and closed, else False.
        """
        async with self._lock:
            if session := self._connections.get(connection_id):
                session.death_signal.set()
                return True

            return False

    def create_grpc_server_credentials(
        self,
        options: SSLServerOptions,
    ) -> grpc.ServerCredentials:
        """
        Create gRPC server SSL credentials from SSLServerOptions.

        :param options: SSLServerOptions containing cert, key and CA paths.

        :return: grpc.ServerCredentials object for secure server setup.
        """

        assert options.cert and options.key and options.ca

        with (
            open(options.cert, "rb") as cert_file,
            open(options.key, "rb") as key_file,
        ):
            server_cert_chain = cert_file.read()
            private_key = key_file.read()

        if options.require_client_cert and options.ca:
            with open(options.ca, "rb") as ca_file:
                root_certificates = ca_file.read()

            return grpc.ssl_server_credentials(
                [(private_key, server_cert_chain)],
                root_certificates=root_certificates,
                require_client_auth=True,
            )

        return grpc.ssl_server_credentials(
            [(private_key, server_cert_chain)],
        )
