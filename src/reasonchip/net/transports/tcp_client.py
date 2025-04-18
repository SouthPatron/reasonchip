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

        assert self._cookie is None
        assert self._callback is None
        assert self._reader is None
        assert self._writer is None
        assert self._handler is None

        try:
            self._sent_none = False

            self._cookie = cookie or uuid.uuid4()

            self._callback = callback

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
            return True

        except Exception:
            self._cookie = None
            self._callback = None
            self._reader = None
            self._writer = None
            self._handler = None

            logging.exception("Connect failed")
            return False

    async def disconnect(self):
        if not self._handler:
            return

        assert self._cookie
        assert self._callback

        self._handler.cancel()

        await asyncio.wait([self._handler])

        if self._sent_none is False:
            await self._callback(self._cookie, None)

        self._cookie = None
        self._callback = None
        self._reader = None
        self._writer = None
        self._handler = None

    async def send_packet(self, packet: SocketPacket) -> bool:
        assert self._writer
        return await send_packet(self._writer, packet)

    async def _loop(self):
        assert self._reader
        assert self._callback
        assert self._cookie

        while True:
            pkt = await receive_packet(self._reader)
            assert pkt is None or isinstance(pkt, SocketPacket)

            await self._callback(self._cookie, pkt)

            if pkt is None:
                self._sent_none = True
                break
