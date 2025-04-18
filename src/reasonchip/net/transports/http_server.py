# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import asyncio
import logging
import uuid
import typing
import ssl

from hypercorn.asyncio import serve
from hypercorn.config import Config

from .http.fastapi.fapi import setup_fapi

from ..protocol import SocketPacket

from .server_transport import (
    ServerTransport,
    NewConnectionCallbackType,
    ReadCallbackType,
    ClosedConnectionCallbackType,
)

from .ssl_options import SSLServerOptions
from .http.common import ClientSession, CallbackHooks


class HttpServer(ServerTransport):

    def __init__(
        self,
        host: str,
        ssl_options: typing.Optional[SSLServerOptions] = None,
    ):
        super().__init__()

        # Information
        self._host: str = host
        self._ssl_options: typing.Optional[SSLServerOptions] = ssl_options
        self._death_signal: asyncio.Event = asyncio.Event()

        # Callbacks
        self._new_connection_callback: typing.Optional[
            NewConnectionCallbackType
        ] = None
        self._read_callback: typing.Optional[ReadCallbackType] = None
        self._closed_connection_callback: typing.Optional[
            ClosedConnectionCallbackType
        ] = None

        # Management
        self._lock: asyncio.Lock = asyncio.Lock()
        self._connections: typing.Dict[uuid.UUID, ClientSession] = {}

        # Hypercorn
        self._server: typing.Optional[asyncio.Task] = None

        cfg: Config = Config()
        cfg.bind = [host]
        cfg.use_reloader = False

        if ssl_options:
            self._apply_ssl_to_config(cfg, ssl_options)

        self._config = cfg

    async def start_server(
        self,
        new_connection_callback: NewConnectionCallbackType,
        read_callback: ReadCallbackType,
        closed_connection_callback: ClosedConnectionCallbackType,
    ) -> bool:

        self._new_connection_callback = new_connection_callback
        self._read_callback = read_callback
        self._closed_connection_callback = closed_connection_callback

        hooks = CallbackHooks(
            self._thunk_new,
            self._thunk_read,
            self._thunk_disconnect,
        )

        app = setup_fapi(callbacks=hooks)

        self._server = asyncio.create_task(
            serve(
                app,  # type: ignore
                self._config,
                shutdown_trigger=self._death_signal.wait,
            )
        )

        logging.info(f"HTTP server listening on {self._host}")
        return True

    async def stop_server(self) -> bool:
        if not self._server:
            return True

        self._death_signal.set()
        await asyncio.wait([self._server])

        self._server = None

        logging.info("HTTP server stopped")
        return True

    async def send_packet(
        self,
        connection_id: uuid.UUID,
        packet: SocketPacket,
    ) -> bool:
        async with self._lock:
            if session := self._connections.get(connection_id):
                await session.outgoing_queue.put(packet)
                return True

            return False

    async def close_connection(self, connection_id: uuid.UUID) -> bool:
        async with self._lock:
            if session := self._connections.get(connection_id):
                session.death_signal.set()
                return True

            return False

    # --------------------- INTERMEDIATE CALLBACKS --------------------------

    async def _thunk_new(self, session: ClientSession):
        assert self._new_connection_callback

        async with self._lock:
            self._connections[session.connection_id] = session
            await self._new_connection_callback(
                self,
                session.connection_id,
            )

    async def _thunk_read(self, session: ClientSession, packet: SocketPacket):
        assert self._read_callback

        async with self._lock:
            assert session.connection_id in self._connections

            await self._read_callback(
                session.connection_id,
                packet,
            )

    async def _thunk_disconnect(self, session: ClientSession):
        assert self._closed_connection_callback

        async with self._lock:
            assert session.connection_id in self._connections

            del self._connections[session.connection_id]

            await self._closed_connection_callback(
                session.connection_id,
            )

    def _apply_ssl_to_config(
        self,
        config: Config,
        ssl_opts: SSLServerOptions,
    ):
        if ssl_opts.cert and ssl_opts.key:
            config.certfile = ssl_opts.cert
            config.keyfile = ssl_opts.key

        if ssl_opts.ca:
            config.ca_certs = ssl_opts.ca

        if ssl_opts.require_client_cert:
            config.verify_mode = ssl.CERT_REQUIRED
        else:
            config.verify_mode = ssl.CERT_OPTIONAL

        if ssl_opts.ciphers:
            config.ciphers = ssl_opts.ciphers
