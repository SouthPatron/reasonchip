# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import uuid
import typing
import logging
import asyncio
import ssl

import httpx

from ..protocol import SocketPacket
from .client_transport import ClientTransport, ReadCallbackType

log = logging.getLogger(__name__)


class HttpClient(ClientTransport):

    def __init__(
        self,
        target: str,
        num_workers: int = 4,
        ssl_context: typing.Optional[ssl.SSLContext] = None,
    ):
        """
        Initialize the HTTP client with target, number of workers, and optional SSL context.

        :param target: The target host address.
        :param num_workers: Number of concurrent worker tasks.
        :param ssl_context: Optional SSL context for HTTPS connections.
        """
        super().__init__()

        # Params and information
        self._callback: typing.Optional[ReadCallbackType] = None
        self._cookie: typing.Optional[uuid.UUID] = None
        self._ssl_context: typing.Optional[ssl.SSLContext] = ssl_context

        # HTTP Client
        if ssl_context:
            self._target = f"https://{target}/v1/stream/stream"
            self._client = httpx.AsyncClient(verify=ssl_context)
        else:
            self._target = f"http://{target}/v1/stream/stream"
            self._client = httpx.AsyncClient()

        # For the workers
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_tasks: list[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        self._num_workers = num_workers

    async def connect(
        self,
        callback: ReadCallbackType,
        cookie: typing.Optional[uuid.UUID] = None,
    ) -> bool:
        """
        Establish connection by setting callback, initializing cookie, and starting worker tasks.

        :param callback: Function to call when a packet is read.
        :param cookie: Optional UUID token; if None, a new UUID will be generated.

        :return: True if connection process initiated successfully.
        """
        assert not self._worker_tasks

        # Set some params
        self._callback = callback
        self._cookie = cookie or uuid.uuid4()
        self._shutdown_event.clear()

        # Start the workers
        self._worker_tasks = [
            asyncio.create_task(self._worker(i))
            for i in range(self._num_workers)
        ]

        log.info(
            f"Connected with cookie: {self._cookie} and {self._num_workers} workers."
        )

        return True

    async def disconnect(self):
        """
        Disconnect by stopping workers, closing HTTP client and clearing callback and cookie.
        """
        if not self._worker_tasks:
            return

        assert self._callback
        assert self._cookie

        # We're dying
        self._shutdown_event.set()

        # Unblock all the workers
        for _ in range(self._num_workers):
            await self._queue.put(None)

        # Let them all die cleanly
        await asyncio.wait(
            self._worker_tasks,
            return_when=asyncio.ALL_COMPLETED,
        )

        self._worker_tasks.clear()

        # Close the HTTP stuff
        await self._client.aclose()

        # Send back the None as per the contract
        await self._callback(self._cookie, None)

        self._callback = None
        self._cookie = None

        log.info("Disconnected and cleaned up resources.")

    async def send_packet(self, packet: SocketPacket) -> bool:
        """
        Enqueue a packet to be sent by the worker tasks.

        :param packet: The SocketPacket to send.

        :return: True if packet was successfully enqueued else False.
        """
        if not self._worker_tasks:
            return False

        await self._queue.put(packet)
        log.debug(f"Packet enqueued: {packet}")
        return True

    async def _worker(self, worker_id: int):
        """
        Worker task to process packets from the queue, send them via HTTP POST, and handle responses.

        :param worker_id: Worker identifier.
        """
        assert self._callback
        assert self._cookie

        try:
            while not self._shutdown_event.is_set():

                packet = await self._queue.get()
                assert packet is None or isinstance(packet, SocketPacket)

                if packet is None:
                    continue

                try:
                    json_data = packet.model_dump_json()
                    response = await self._client.post(
                        self._target,
                        content=json_data,
                        timeout=None,
                    )

                    if response.status_code != 200:
                        log.error(
                            f"[Worker {worker_id}] HTTP error: {response.status_code}"
                        )
                        continue

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        try:
                            pkt = SocketPacket.model_validate_json(line)
                            await self._callback(self._cookie, pkt)
                        except Exception:
                            log.exception(
                                f"[Worker {worker_id}] Failed to parse line: {line}"
                            )

                except Exception:
                    log.exception(
                        f"[Worker {worker_id}] failed to process packet"
                    )

        except asyncio.CancelledError:
            log.info(f"[Worker {worker_id}] cancelled")

        except Exception:
            log.exception(f"[Worker {worker_id}] unexpected error")
