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

from .protocol import (
    SocketPacket,
    PacketType,
    ResultCode,
)

log = logging.getLogger("reasonchip.net.task_manager")


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
        max_capacity: int = 4,
    ):
        log.debug(f"Creating TaskManager with capacity {max_capacity}")

        assert max_capacity > 0

        # General state
        self._engine: Engine = engine
        self._max_capacity: int = max_capacity
        self._lock: asyncio.Lock = asyncio.Lock()

        # Streams
        self._incoming_queue: asyncio.Queue = asyncio.Queue()
        self._sem: asyncio.Semaphore = asyncio.Semaphore()

        # Multiplexing
        self._dying: asyncio.Event = asyncio.Event()
        self._handler: typing.Optional[asyncio.Task] = None
        self._tasks: typing.Dict[uuid.UUID, TaskInfo] = {}

        log.debug(f"TaskManager created")

    # ------------------------- LIFECYCLE ------------------------------------

    async def start(self):
        log.info(f"Starting TaskManager...")

        assert self._handler is None

        self._dying.clear()

        log.info("Spawning the multiplexing task...")

        self._handler = asyncio.create_task(self._multiplexing())

        log.info(f"TaskManager started...")

    async def wait(self, timeout: typing.Optional[float] = None) -> bool:
        log.info(f"Waiting for TaskManager to finish: timeout=[{timeout}] ...")

        if self._handler is None:
            log.warning("TaskManager is already dead")
            return True

        assert self._handler is not None

        done, _ = await asyncio.wait([self._handler], timeout=timeout)
        if not done:
            log.debug("Timeout occurred")
            return False

        self._handler = None

        log.info(f"TaskManager is finished.")
        return True

    async def stop(self, timeout: typing.Optional[float] = None) -> bool:
        log.debug(f"Stopping TaskManager...")

        if not self._dying.is_set():
            self._dying.set()

        rc = await self.wait(timeout=timeout)
        if rc is False:
            log.info(f"Timeout occurred while stopping TaskManager.")
            return False

        log.info(f"TaskManager stopped.")
        return True

    # ------------------------- QUEUEING -------------------------------------

    async def queue(
        self,
        packet: SocketPacket,
        timeout: typing.Optional[float] = None,
    ) -> bool:

        # We will wait for the timeout, semaphore, or the task to die.
        t_dying = asyncio.create_task(self._dying.wait())
        t_queue = asyncio.create_task(self._sem.acquire())

        # Let's do this.
        done, _ = await asyncio.wait(
            [t_dying, t_queue],
            timeout=timeout,
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Timeout occurred
        if not done:
            t_dying.cancel()
            t_queue.cancel()
            return False

        # We are actually dying
        if t_dying in done:
            t_queue.cancel()
            return False

        t_dying.cancel()

        # We acquired the semaphore. We can queue.
        await self._incoming_queue.put(packet)
        return True

    # ------------------------- PLEXORS --------------------------------------

    async def _wait_for_engine(
        self,
        task: asyncio.Task,
        cookie: uuid.UUID,
    ) -> uuid.UUID:

        log.debug(f"Waiting for engine run to complete: {cookie}")

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

        log.debug(f"Entering multiplexing loop")

        # Create the tasks
        t_dying = asyncio.create_task(self._dying.wait())
        t_incoming = asyncio.create_task(self._incoming_queue.get())

        wl = [t_dying, t_incoming]

        # Release all necessary semaphores
        for _ in range(self._max_capacity):
            self._sem.release()

        # Now loop until we are dying and there are no more tasks
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

                wl.remove(t)

                cookie = t.result()
                assert isinstance(cookie, uuid.UUID)
                self._tasks.pop(cookie)

                # Release the semaphore for the task
                self._sem.release()

                log.debug(f"Recognized task completion: {cookie}")

            # Consider death
            if t_dying in done:
                assert t_dying and t_dying.done()

                wl.remove(t_dying)

                t_dying = None

                log.debug("Started dying because we were requested to die")

                if t_incoming:
                    t_incoming.cancel()

            # Receiving a packet
            if t_incoming in done:
                assert t_incoming and t_incoming.done()

                log.debug("Received packet on incoming queue")

                wl.remove(t_incoming)

                rc = t_incoming.result()

                t_incoming = None

                assert rc is None or isinstance(rc, SocketPacket)

                restart = await self._process_server_packet(rc)

                # Restart the task if advised and we're not dying
                if restart and not self._dying.is_set():
                    log.debug("Restarting the incoming queue task")
                    t_incoming = asyncio.create_task(self._incoming_queue.get())

                    wl.append(t_incoming)

                else:
                    if not self._dying.is_set():
                        self._dying.set()
                    log.debug("Not restarting the incoming queue task")

            # Rebuild the waiting list, adding any running engines
            wl = [x for x in (t_dying, t_incoming) if x is not None]

            for t in self._tasks.values():
                assert t.task is not None
                wl.append(
                    asyncio.create_task(self._wait_for_engine(t.task, t.cookie))
                )

        log.debug(f"Exiting multiplexing loop")

    # ------------------------- HANDLERS -------------------------------------

    async def _process_server_packet(
        self,
        packet: SocketPacket,
    ) -> typing.Optional[TaskInfo]:

        log.debug(
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

    async def _srv_run(self, packet: SocketPacket) -> typing.Optional[TaskInfo]:
        # Make sure we have capacity
        if len(self._tasks) >= self._max_capacity:
            log.fatal(
                "Capacity reached on worker. We should never have been asked."
            )
            return None

        # Check if the packet is fine
        if not packet.cookie or not packet.workflow:
            log.fatal(
                "Missing cookie or pipeline in packet. Should have been checked beforehand."
            )
            return None

        # Check for collisions
        if packet.cookie in self._tasks:
            log.fatal(
                "Cookie collision has occurred. Should never have been allowed."
            )
            return None

        # Create a new task
        task_info = TaskInfo(cookie=packet.cookie)
        self._tasks[packet.cookie] = task_info

        task_info.task = asyncio.create_task(
            self._run_engine(
                task_info,
                workflow=packet.workflow,
                variables=packet.variables,
            )
        )

        return task_info

    async def _srv_cancel(
        self, packet: SocketPacket
    ) -> typing.Optional[TaskInfo]:
        # Check if the packet is fine
        if not packet.cookie:
            log.fatal("Missing cookie. Should have been checked beforehand.")
            return None

        # Check for the task
        if packet.cookie not in self._tasks:
            log.warning(
                f"Cookie not found trying to cancel. Could be a race condition: [{packet.cookie}]"
            )
            return None

        log.info(f"Cancelling task: [{packet.cookie}]")

        task_info = self._tasks[packet.cookie]
        assert task_info.task is not None
        task_info.task.cancel()
        return None

    async def _srv_shutdown(
        self, packet: SocketPacket
    ) -> typing.Optional[TaskInfo]:
        log.info(f"Shutdown request received from server")
        return None

    async def _srv_unsupported_packet_type(
        self, packet: SocketPacket
    ) -> typing.Optional[TaskInfo]:
        log.fatal(f"Unsupported packet type: [{packet.packet_type}]")
        return None

    # ------------------------- ENGINE RUNNER --------------------------------

    async def _run_engine(
        self,
        task_info: TaskInfo,
        workflow: str,
        variables: typing.Optional[str] = None,
    ):
        start_time = time.perf_counter()

        try:
            log.info(f"Running engine: [{task_info.cookie}] [{workflow}]")

            # Process the variables
            v = json.loads(variables) if variables else {}

            # Run the engine
            rc = await self._engine.run(entry=workflow, **v)

            log.debug(
                f"Engine run completed: [{task_info.cookie}] [{workflow}] [{rc}]"
            )

        except Exception:
            log.exception(
                f"Exception occurred during engine run: [{task_info.cookie}] [{workflow}]"
            )

        end_time = time.perf_counter()

        elapsed = (end_time - start_time) * 1_000_000

        time_ms = elapsed / 1_000
        time_s = time_ms / 1_000

        log.info(
            f"Engine task completed: [{task_info.cookie}] [{workflow}] [{elapsed:.2f}us] [{time_ms:.2f}ms] [{time_s:.2f}s]"
        )
