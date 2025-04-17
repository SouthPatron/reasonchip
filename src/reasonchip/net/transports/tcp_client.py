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


class TcpClient(ClientTransport):
    """
    A transport which connects to a TCP socket.
    """

    def __init__(
        self,
        host=None,
        port=None,
        limit=2**16,
        ssl=None,
        family=0,
        proto=0,
        flags=0,
        sock=None,
        local_addr=None,
        server_hostname=None,
        ssl_handshake_timeout=None,
        ssl_shutdown_timeout=None,
        happy_eyeballs_delay=None,
        interleave=None,
    ):
        """
        Constructor.

        Maps directly to `asyncio.open_connection`.

        :param host: The host name or IP to connect to.
        :param port: The port number to connect to.
        :param limit: Stream reader buffer limit.
        :param ssl: SSL context or None.
        :param family: Socket family.
        :param proto: Socket protocol.
        :param flags: Socket flags.
        :param sock: Custom socket.
        :param local_addr: Local address to bind.
        :param server_hostname: Hostname for SSL handshake.
        :param ssl_handshake_timeout: Timeout for SSL handshake.
        :param ssl_shutdown_timeout: Timeout for SSL shutdown.
        :param happy_eyeballs_delay: Delay for Happy Eyeballs algorithm.
        :param interleave: Interleave setting.
        """
        super().__init__()

        # TCP values
        self._host = host
        self._port = port
        self._limit = limit
        self._ssl = ssl
        self._family = family
        self._proto = proto
        self._flags = flags
        self._sock = sock
        self._local_addr = local_addr
        self._server_hostname = server_hostname
        self._ssl_handshake_timeout = ssl_handshake_timeout
        self._ssl_shutdown_timeout = ssl_shutdown_timeout
        self._happy_eyeballs_delay = happy_eyeballs_delay
        self._interleave = interleave

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
        Connect to the TCP server.

        :param callback: The callback to invoke on received data.
        :param cookie: Optional cookie identifier for this connection.

        :return: True if connection succeeds, False otherwise.
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

            log.info(
                f"Connecting to {self._host}:{self._port} with cookie {self._cookie}"
            )

            self._reader, self._writer = await asyncio.open_connection(
                host=self._host,
                port=self._port,
                limit=self._limit,
                ssl=self._ssl,
                family=self._family,
                proto=self._proto,
                flags=self._flags,
                sock=self._sock,
                local_addr=self._local_addr,
                server_hostname=self._server_hostname,
                ssl_handshake_timeout=self._ssl_handshake_timeout,
                ssl_shutdown_timeout=self._ssl_shutdown_timeout,
                happy_eyeballs_delay=self._happy_eyeballs_delay,
                interleave=self._interleave,
            )

            self._handler = asyncio.create_task(self._loop())
            log.info(f"Connection established with cookie {self._cookie}")
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
        Disconnect the current TCP connection.
        """
        if not self._handler:
            log.info("Disconnect called but no active handler.")
            return

        assert self._cookie
        assert self._callback

        log.info(f"Disconnecting connection with cookie {self._cookie}")

        self._handler.cancel()

        # Wait for handler task to finish
        await asyncio.wait([self._handler])

        # Notify callback with None if not already done
        if self._sent_none is False:
            await self._callback(self._cookie, None)

        self._cookie = None
        self._callback = None
        self._reader = None
        self._writer = None
        self._handler = None

        log.info("Disconnected successfully")

    async def send_packet(self, packet: SocketPacket) -> bool:
        """
        Send a packet over the TCP connection.

        :param packet: The packet to send.

        :return: True if sent successfully, False otherwise.
        """
        assert self._writer
        log.debug(f"Sending packet: {packet}")
        return await send_packet(self._writer, packet)

    async def _loop(self):
        """
        Internal receive loop that listens for incoming packets
        and dispatches them to the callback.
        """
        assert self._reader
        assert self._callback
        assert self._cookie

        log.info(f"Started receive loop with cookie {self._cookie}")

        while True:
            pkt = await receive_packet(self._reader)
            assert pkt is None or isinstance(pkt, SocketPacket)

            log.debug(f"Received packet: {pkt}")

            await self._callback(self._cookie, pkt)

            if pkt is None:
                self._sent_none = True
                log.info(
                    f"Received None packet, terminating receive loop for cookie {self._cookie}"
                )
                break
