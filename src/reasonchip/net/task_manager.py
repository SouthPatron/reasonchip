# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import uuid
import asyncio
import json
import logging
import time

from dataclasses import dataclass

from reasonchip.core.engine.engine import Engine

log = logging.getLogger("reasonchip.net.task_manager")


@dataclass
class TaskInfo:
    cookie: uuid.UUID
    workflow: str
    params: typing.Optional[str] = None
    task: typing.Optional[asyncio.Task] = None


class TaskManager:
    """
    TaskManager manages multiple engine tasks up to a capacity.
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
        self._incoming_queue: asyncio.Queue[TaskInfo] = asyncio.Queue[
            TaskInfo
        ]()
        self._sem: asyncio.Semaphore = asyncio.Semaphore()

        # Multiplexing
        self._dying: asyncio.Event = asyncio.Event()
        self._handler: typing.Optional[asyncio.Task] = None
        self._tasks: typing.Dict[uuid.UUID, TaskInfo] = {}

        log.debug(f"TaskManager created")

    # ------------------------- PROPERTIES -----------------------------------

    def task(self) -> asyncio.Task:
        assert self._handler is not None
        return self._handler

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
        cookie: uuid.UUID,
        workflow: str,
        params: typing.Optional[str] = None,
        timeout: typing.Optional[float] = None,
    ) -> bool:

        log.debug(
            f"Queueing task: [{cookie}] [{workflow}] [{params}] with timeout={timeout}"
        )

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
            log.debug("Queueing task timed out")
            t_dying.cancel()
            t_queue.cancel()
            await asyncio.gather(t_dying, t_queue, return_exceptions=True)
            return False

        # We are actually dying
        if t_dying in done:
            log.debug("Queueing task was cancelled because we are dying")
            t_queue.cancel()
            await asyncio.gather(t_queue, return_exceptions=True)
            return False

        # We acquired the semaphore
        assert t_queue in done and t_queue.done()

        log.debug("Semaphore acquired, proceeding with queueing")

        t_dying.cancel()
        await asyncio.gather(t_dying, return_exceptions=True)

        # Queue the request
        await self._incoming_queue.put(
            TaskInfo(
                cookie=cookie,
                workflow=workflow,
                params=params,
            )
        )
        return True

    # ------------------------- PLEXORS --------------------------------------

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

            # Handle an engine completion
            for t in done:
                if t in (t_dying, t_incoming):
                    continue

                assert t and t.done()

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
                assert t_incoming

                wl.remove(t_incoming)

                if t_incoming.cancelled():
                    # Handle cancelled tasks
                    log.debug("Incoming task was cancelled")
                    t_incoming = None
                    continue

                assert t_incoming.done()

                log.debug("Received packet on incoming queue")

                rc = t_incoming.result()

                t_incoming = None

                # Create and record the task
                rc.task = asyncio.create_task(self._run_engine(rc))
                self._tasks[rc.cookie] = rc
                wl.append(rc.task)

                # Restart the task if we're not dying
                if not self._dying.is_set():
                    log.debug("Restarting the incoming queue task")
                    t_incoming = asyncio.create_task(self._incoming_queue.get())
                    wl.append(t_incoming)

        log.debug(f"Exiting multiplexing loop")

    # ------------------------- ENGINE RUNNER --------------------------------

    async def _run_engine(self, task_info: TaskInfo):
        start_time = time.perf_counter()

        try:
            log.info(
                f"Running engine: [{task_info.cookie}] [{task_info.workflow}]"
            )

            # Process the variables
            v = json.loads(task_info.params) if task_info.params else {}

            # Run the engine
            rc = await self._engine.run(entry=task_info.workflow, **v)

            log.debug(
                f"Engine run completed: [{task_info.cookie}] [{task_info.workflow}] [{rc}]"
            )

        except Exception:
            log.exception(
                f"Exception occurred during engine run: [{task_info.cookie}] [{task_info.workflow}]"
            )

        end_time = time.perf_counter()

        elapsed = (end_time - start_time) * 1_000_000

        time_ms = elapsed / 1_000
        time_s = time_ms / 1_000

        log.info(
            f"Engine task completed: [{task_info.cookie}] [{task_info.workflow}] [{elapsed:.2f}us] [{time_ms:.2f}ms] [{time_s:.2f}s]"
        )

        return task_info.cookie
