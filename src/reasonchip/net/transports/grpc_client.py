#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import logging
import asyncio
import uuid

import grpc
import grpc.aio

from ..protocol import SocketPacket

from .ssl_options import SSLClientOptions

from .client_transport import ClientTransport, ReadCallbackType

from .grpc_stubs.reasonchip_pb2_grpc import ReasonChipServiceStub

log = logging.getLogger(__name__)


class GrpcClient(ClientTransport):

    def __init__(
        self,
        target: str,
        ssl_options: typing.Optional[SSLClientOptions] = None,
    ):
        """
        Initialize the gRPC client transport.

        :param target: The server target address in the format `host:port`.
        :param ssl_options: Optional SSL options for secure connection.
        """
        super().__init__()

        # Parameters
        self._target = target

        # Integration stuff
        self._cookie: typing.Optional[uuid.UUID] = None
        self._callback: typing.Optional[ReadCallbackType] = None
        self._sent_none: bool = False

        # gRPC specific and supports
        self._channel: typing.Optional[grpc.aio.Channel] = None
        self._stub: typing.Optional[ReasonChipServiceStub] = None
        self._outgoing_queue: typing.Optional[asyncio.Queue] = None
        self._task: typing.Optional[asyncio.Task] = None

        # SSL
        self._ssl_options: typing.Optional[SSLClientOptions] = ssl_options

    async def connect(
        self,
        callback: ReadCallbackType,
        cookie: typing.Optional[uuid.UUID] = None,
    ) -> bool:
        """
        Establish a connection to the gRPC server.

        :param callback: Callback invoked on receiving packets.
        :param cookie: Optional identifier for connection context.

        :return: True if connection successful, False otherwise.
        """
        assert self._channel is None
        assert self._callback is None
        assert self._outgoing_queue is None
        assert self._task is None

        try:
            self._sent_none = False

            self._cookie = cookie or uuid.uuid4()
            self._outgoing_queue = asyncio.Queue()
            self._callback = callback

            if self._ssl_options:
                self._channel = self.create_secure_grpc_channel(
                    self._target,
                    self._ssl_options,
                )
            else:
                self._channel = grpc.aio.insecure_channel(self._target)

            self._stub = ReasonChipServiceStub(self._channel)

            self._task = asyncio.create_task(self._loop())
            log.info(
                f"Connected to gRPC server at {self._target} with cookie {self._cookie}"
            )
            return True

        except Exception:
            log.exception("gRPC connection failed")
            self._sent_none = False
            self._cookie = None
            self._outgoing_queue = None
            self._callback = None
            self._channel = None
            self._stub = None
            self._task = None
            return False

    async def disconnect(self):
        """
        Disconnect from the gRPC server and cleanup resources.
        """
        if not self._task:
            return

        assert self._cookie
        assert self._channel

        self._task.cancel()

        # Wait for the running task to finish
        await asyncio.wait([self._task])

        # Notify callback that connection is closed by sending None
        if not self._sent_none and self._callback:
            await self._callback(self._cookie, None)

        await self._channel.close()

        # Reset internal state
        self._sent_none = False
        self._cookie = None
        self._outgoing_queue = None
        self._callback = None
        self._channel = None
        self._stub = None
        self._task = None

        log.info("Disconnected from gRPC server")

    # -------------------------- TUNNELS --------------------------------------

    async def send_packet(self, packet: SocketPacket) -> bool:
        """
        Send a packet to the gRPC server.

        :param packet: Packet to be sent.

        :return: True if successfully added to queue, False otherwise.
        """
        # Just let caller know, to the best of our ability
        if self._outgoing_queue is None:
            log.warning("Cannot send packet: outgoing queue not initialized")
            return False

        await self._outgoing_queue.put(packet)
        log.debug(f"Packet enqueued for sending: {packet}")
        return True

    # -------------------------- LOOPSKIES ------------------------------------

    async def _loop(self):
        """
        Main send/receive loop to handle gRPC streaming.

        Retrieves packets from the outgoing queue and streams them to the server,
        while processing incoming packets via the callback.
        """
        assert self._stub
        assert self._callback
        assert self._cookie
        assert self._outgoing_queue

        async def packet_stream(queue: asyncio.Queue):
            while True:
                packet = await queue.get()
                yield packet

        try:
            response_stream = self._stub.EstablishConnection(
                packet_stream(self._outgoing_queue)
            )

            async for packet in response_stream:
                await self._callback(self._cookie, packet)

        except Exception as e:
            log.warning(f"gRPC receive error: {e}")

        finally:
            self._sent_none = True
            await self._callback(self._cookie, None)

    # -------------------------- STUFF ----------------------------------------

    def create_secure_grpc_channel(
        self,
        target: str,
        options: SSLClientOptions,
    ) -> grpc.aio.Channel:
        """
        Create a secure gRPC channel using SSL credentials.

        :param target: Target server address.
        :param options: SSLClientOptions containing CA, cert and key paths.

        :return: A secure gRPC channel.
        """
        assert options.ca

        with open(options.ca, "rb") as ca_file:
            trusted_certs = ca_file.read()

        if options.cert and options.key:
            with (
                open(options.cert, "rb") as cert_file,
                open(options.key, "rb") as key_file,
            ):
                client_cert = cert_file.read()
                client_key = key_file.read()

            creds = grpc.ssl_channel_credentials(
                root_certificates=trusted_certs,
                private_key=client_key,
                certificate_chain=client_cert,
            )

        else:
            creds = grpc.ssl_channel_credentials(
                root_certificates=trusted_certs
            )

        log.info(f"Created secure gRPC channel to {target}")
        return grpc.aio.secure_channel(target, creds)
