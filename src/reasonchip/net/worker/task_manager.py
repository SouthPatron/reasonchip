# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import uuid
import asyncio
import traceback
import json
import logging
import time

from dataclasses import dataclass

from reasonchip.core.engine.engine import Engine
from reasonchip.core.engine.variables import Variables

from ..transports import ClientTransport

from ..protocol import (
    SocketPacket,
    PacketType,
    ResultCode,
)


@dataclass
class TaskInfo:
    cookie: uuid.UUID
    task: typing.Optional[asyncio.Task] = None


class TaskManager:
    """
    TaskManager manages multiple engine tasks across a transport connection
    to a server.
    """

    def __init__(
        self,
        engine: Engine,
        transport: ClientTransport,
        max_capacity: int = 4,
    ):
        logging.debug(f"Creating TaskManager with capacity {max_capacity}")

        assert max_capacity > 0

        # General state
        self._engine: Engine = engine
        self._transport: ClientTransport = transport
        self._max_capacity: int = max_capacity

        # Streams
        self._incoming_queue: asyncio.Queue = asyncio.Queue()

        # Multiplexing
        self._dying: asyncio.Event = asyncio.Event()
        self._handler: typing.Optional[asyncio.Task] = None
        self._tasks: typing.Dict[uuid.UUID, TaskInfo] = {}

        logging.debug(f"TaskManager created")

    # ------------------------- LIFECYCLE ------------------------------------

    async def start(self):
        logging.info(f"Starting TaskManager...")

        assert self._handler is None

        self._dying.clear()

        logging.info(f"Starting Transport...")

        rc = await self._transport.connect(callback=self._incoming_packet)
        if rc is False:
            raise ConnectionError("Failed to connect the transport")

        logging.info("Spawning the multiplexing task...")

        self._handler = asyncio.create_task(self._multiplexing())

        # Send the register packet
        logging.info("Sending registration packet...")
        rc = await self._transport.send_packet(
            SocketPacket(
                packet_type=PacketType.REGISTER,
                capacity=self._max_capacity,
            )
        )
        if rc is False:
            raise ConnectionError("Failed to send registration packet")

        logging.info(f"TaskManager started...")

    async def wait(self, timeout: typing.Optional[float] = None) -> bool:
        logging.info(
            f"Waiting for TaskManager to finish: timeout=[{timeout}] ..."
        )

        if self._handler is None:
            logging.warning("TaskManager is already dead")
            return True

        assert self._handler is not None

        done, _ = await asyncio.wait([self._handler], timeout=timeout)
        if not done:
            logging.debug("Timeout occurred")
            return False

        self._handler = None

        logging.info(f"TaskManager is finished.")
        return True

    async def stop(self, timeout: typing.Optional[float] = None) -> bool:
        logging.debug(f"Stopping TaskManager...")

        if not self._dying.is_set():
            self._dying.set()

        rc = await self.wait(timeout=timeout)
        if rc is False:
            logging.info(f"Timeout occurred while stopping TaskManager.")
            return False

        logging.info(f"TaskManager stopped.")
        return True

    # ------------------------- PLEXORS --------------------------------------

    async def _incoming_packet(
        self,
        cookie: uuid.UUID,
        packet: typing.Optional[SocketPacket],
    ):
        logging.debug(f"Received packet on task manager")
        await self._incoming_queue.put(packet)

    async def _wait_for_engine(
        self,
        task: asyncio.Task,
        cookie: uuid.UUID,
    ) -> uuid.UUID:

        logging.debug(f"Waiting for engine run to complete: {cookie}")

        # Wait for an engine run to complete
        done, _ = await asyncio.wait(
            [task],
            return_when=asyncio.ALL_COMPLETED,
        )
        assert done

        ex = task.exception()
        assert ex is None
        return cookie

    async def _multiplexing(self):

        logging.debug(f"Entering multiplexing loop")

        t_dying = asyncio.create_task(self._dying.wait())
        t_incoming = asyncio.create_task(self._incoming_queue.get())

        wl = [t_dying, t_incoming]

        while wl:
            done, _ = await asyncio.wait(
                wl,
                return_when=asyncio.FIRST_COMPLETED,
            )
            assert done

            # Handle tasks
            for t in done:
                if t in (t_dying, t_incoming):
                    continue

                cookie = t.result()
                assert isinstance(cookie, uuid.UUID)
                self._tasks.pop(cookie)

                logging.debug(f"Recognized task completion: {cookie}")

            # Consider death
            if t_dying in done:
                assert t_dying and t_dying.done()
                t_dying = None

                logging.debug("Started dying because we were requested to die")

                if t_incoming:
                    t_incoming.cancel()

            # Receiving a packet
            if t_incoming in done:
                assert t_incoming and t_incoming.done()

                logging.debug("Received packet on incoming queue")

                rc = t_incoming.result()

                t_incoming = None

                assert rc is None or isinstance(rc, SocketPacket)

                restart = await self._process_server_packet(rc)

                # Restart the task if advised and we're not dying
                if restart and not self._dying.is_set():
                    logging.debug("Restarting the incoming queue task")
                    t_incoming = asyncio.create_task(self._incoming_queue.get())
                else:
                    if not self._dying.is_set():
                        self._dying.set()
                    logging.debug("Not restarting the incoming queue task")

            # Rebuild the waiting list, adding any running engines
            wl = [x for x in (t_dying, t_incoming) if x is not None]

            for t in self._tasks.values():
                assert t.task is not None
                wl.append(
                    asyncio.create_task(self._wait_for_engine(t.task, t.cookie))
                )

        assert self._transport is not None
        await self._transport.disconnect()

        logging.debug(f"Exiting multiplexing loop")

    # ------------------------- HANDLERS -------------------------------------

    async def _process_server_packet(
        self,
        packet: typing.Optional[SocketPacket] = None,
    ) -> bool:

        # The incoming connection is dead.
        if packet is None:
            logging.warning("Received None on incoming queue. Time to die.")
            return False

        logging.debug(
            f"Processing server packet: [{packet.packet_type}] [{packet.cookie}]"
        )

        handlers = {
            PacketType.SHUTDOWN: self._srv_shutdown,
            PacketType.RUN: self._srv_run,
            PacketType.CANCEL: self._srv_cancel,
        }

        handler = handlers.get(
            packet.packet_type, self._srv_unsupported_packet_type
        )
        return await handler(packet)

    async def _srv_run(self, packet: SocketPacket) -> bool:
        # Make sure we have capacity
        if len(self._tasks) >= self._max_capacity:
            logging.fatal(
                "Capacity reached on worker. We should never have been asked."
            )
            return False

        # Check if the packet is fine
        if not packet.cookie or not packet.pipeline:
            logging.fatal(
                "Missing cookie or pipeline in packet. Should have been checked beforehand."
            )
            return False

        # Check for collisions
        if packet.cookie in self._tasks:
            logging.fatal(
                "Cookie collision has occurred. Should never have been allowed."
            )
            return False

        # Create a new task
        task_info = TaskInfo(cookie=packet.cookie)
        self._tasks[packet.cookie] = task_info

        task_info.task = asyncio.create_task(
            self._run_engine(
                task_info,
                pipeline=packet.pipeline,
                variables=packet.variables,
            )
        )

        return True

    async def _srv_cancel(self, packet: SocketPacket) -> bool:
        # Check if the packet is fine
        if not packet.cookie:
            logging.fatal(
                "Missing cookie. Should have been checked beforehand."
            )
            return False

        # Check for the task
        if packet.cookie not in self._tasks:
            logging.warning(
                f"Cookie not found trying to cancel. Could be a race condition: [{packet.cookie}]"
            )
            return True

        logging.info(f"Cancelling task: [{packet.cookie}]")

        task_info = self._tasks[packet.cookie]
        assert task_info.task is not None
        task_info.task.cancel()
        return True

    async def _srv_shutdown(self, packet: SocketPacket) -> bool:
        logging.info(f"Shutdown request received from server")
        return False

    async def _srv_unsupported_packet_type(self, packet: SocketPacket) -> bool:
        logging.fatal(f"Unsupported packet type: [{packet.packet_type}]")
        return False

    # ------------------------- ENGINE RUNNER --------------------------------

    async def _run_engine(
        self,
        task_info: TaskInfo,
        pipeline: str,
        variables: typing.Optional[str] = None,
    ):
        start_time = time.perf_counter()

        try:
            logging.info(f"Running engine: [{task_info.cookie}] [{pipeline}]")

            # Process the variables
            v = json.loads(variables) if variables else {}
            vobj = Variables(v)

            # Run the engine
            rc = await self._engine.run(
                entry=pipeline,
                variables=vobj,
            )

            # Serialize the results
            rc_str = json.dumps(rc) if rc else None

            await self._transport.send_packet(
                SocketPacket(
                    packet_type=PacketType.RESULT,
                    cookie=task_info.cookie,
                    rc=ResultCode.OK,
                    result=rc_str,
                )
            )

        except Exception as e:
            logging.exception(
                f"Exception occurred during engine run: [{task_info.cookie}] [{pipeline}]"
            )

            await self._transport.send_packet(
                SocketPacket(
                    packet_type=PacketType.RESULT,
                    cookie=task_info.cookie,
                    rc=ResultCode.EXCEPTION,
                    error=str(e),
                    stacktrace=traceback.format_exception(e),
                    result=None,
                )
            )

        end_time = time.perf_counter()

        elapsed = (end_time - start_time) * 1_000_000

        time_ms = elapsed / 1_000
        time_s = time_ms / 1_000

        logging.info(
            f"Engine task completed: [{task_info.cookie}] [{pipeline}] [{elapsed:.2f}us] [{time_ms:.2f}ms] [{time_s:.2f}s]"
        )
