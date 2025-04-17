# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import uuid
import asyncio
import logging

from ..protocol import receive_packet, send_packet, SocketPacket

from .client_transport import ClientTransport, ReadCallbackType

log = logging.getLogger(__name__)


class SocketClient(ClientTransport):
    """
    A transport which connects to a UNIX socket.
    """

    def __init__(
        self,
        path: str,
        limit: int = 2**16,
        sock=None,
        ssl=None,
        server_hostname=None,
        ssl_handshake_timeout=None,
        ssl_shutdown_timeout=None,
    ):
        """
        Constructor.

        No typing here just to send through as received.

        Maps directly to `asyncio.open_unix_connection`.

        :param path: The path to the UNIX socket.
        :param limit: Buffer limit for the connection.
        :param sock: Optional pre-existing socket.
        :param ssl: SSL context if using SSL.
        :param server_hostname: Hostname for SSL server.
        :param ssl_handshake_timeout: Timeout for SSL handshake.
        :param ssl_shutdown_timeout: Timeout for SSL shutdown.
        """
        super().__init__()

        # Socket values
        self._path: str = path
        self._limit = limit or 2**16
        self._sock = sock
        self._ssl = ssl
        self._server_hostname = server_hostname
        self._ssl_handshake_timeout = ssl_handshake_timeout
        self._ssl_shutdown_timeout = ssl_shutdown_timeout

        # Comms
        self._cookie: typing.Optional[uuid.UUID] = None
        self._callback: typing.Optional[ReadCallbackType] = None
        self._reader: typing.Optional[asyncio.StreamReader] = None
        self._writer: typing.Optional[asyncio.StreamWriter] = None
        self._handler: typing.Optional[asyncio.Task] = None
        self._sent_none: bool = False

    async def connect(
        self,
        callback: ReadCallbackType,
        cookie: typing.Optional[uuid.UUID] = None,
    ) -> bool:
        """
        Connects to the UNIX socket and prepares for reading and writing.

        :param callback: The callback function to handle received packets.
        :param cookie: Optional UUID for the connection session.

        :return: True if connection is successful, False otherwise.
        """

        assert self._cookie is None
        assert self._callback is None
        assert self._reader is None
        assert self._writer is None
        assert self._handler is None

        try:
            self._sent_none = False

            self._cookie = cookie or uuid.uuid4()

            self._callback = callback

            self._reader, self._writer = await asyncio.open_unix_connection(
                path=self._path,
                limit=self._limit,
                sock=self._sock,
                ssl=self._ssl,
                server_hostname=self._server_hostname,
                ssl_handshake_timeout=self._ssl_handshake_timeout,
                ssl_shutdown_timeout=self._ssl_shutdown_timeout,
            )

            self._handler = asyncio.create_task(self._loop())

            log.info(
                f"Connected to UNIX socket at {self._path} with cookie {self._cookie}"
            )

            return True

        except Exception:
            self._cookie = None
            self._callback = None
            self._reader = None
            self._writer = None
            self._handler = None

            log.exception("Connect failed")
            return False

    async def disconnect(self):
        """
        Disconnects from the socket and cleans up resources.
        """
        if not self._handler:
            return

        assert self._cookie
        assert self._callback

        # Cancel the handler task
        self._handler.cancel()

        # Wait for the handler to finish
        await asyncio.wait([self._handler])

        # If no None packet sent yet, send callback with None
        if self._sent_none is False:
            await self._callback(self._cookie, None)

        # Clear all state
        self._cookie = None
        self._callback = None
        self._reader = None
        self._writer = None
        self._handler = None

        log.info(f"Disconnected from UNIX socket at {self._path}")

    async def send_packet(self, packet: SocketPacket) -> bool:
        """
        Sends a packet to the socket.

        :param packet: The packet to send.

        :return: True if sending was successful, False otherwise.
        """
        assert self._writer
        result = await send_packet(self._writer, packet)
        log.info(f"Sent packet {packet} to UNIX socket at {self._path}")
        return result

    async def _loop(self):
        """
        Loop that continuously receives packets from the socket and calls the callback.
        """
        assert self._reader
        assert self._callback
        assert self._cookie

        # Continuously receive packets and invoke the callback
        while True:
            pkt = await receive_packet(self._reader)

            # Ensure packet is None or of type SocketPacket
            assert pkt is None or isinstance(pkt, SocketPacket)

            await self._callback(self._cookie, pkt)

            if pkt is None:
                self._sent_none = True
                log.info(
                    f"Received termination packet on UNIX socket at {self._path}"
                )
                break
