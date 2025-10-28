import typing
import asyncio

from abc import ABC, abstractmethod


class SimpleTask(ABC):

    def __init__(self, name: str):
        super().__init__()

        # Task Management
        self._name: str = name
        self._task: typing.Optional[asyncio.Task] = None
        self._stop_event: asyncio.Event = asyncio.Event()
        self._task: typing.Optional[asyncio.Task] = None
        self._failed: bool = False
        self._exception: typing.Optional[Exception] = None

    # ------------------- PROPERTIES -----------------------------------------

    @property
    def name(self) -> str:
        return self._name

    @property
    def failed(self) -> bool:
        return self._failed

    @property
    def exception(self) -> typing.Optional[Exception]:
        return self._exception

    # ------------------ TASK CONTROL ----------------------------------------

    def task(self) -> asyncio.Task:
        assert self._task is not None
        return self._task

    def keep_running(self) -> bool:
        assert self._task is not None
        return self._stop_event.is_set() is False

    async def start(self) -> None:
        assert self._task is None

        self._stop_event.clear()
        self._task = asyncio.create_task(
            self.run(),
            name=self._name,
        )

    async def stop(self) -> None:
        assert self._task is not None
        self._stop_event.set()

    async def cancel(self) -> bool:
        assert self._task is not None
        return self._task.cancel()

    async def wait(self, timeout: float) -> bool:
        assert self._task is not None
        done, _ = await asyncio.wait([self._task], timeout=timeout)
        return len(done) == 1

    async def run(self) -> None:
        assert self._task is not None

        try:
            await self.impl()
        except Exception as e:
            self._exception = e
            self._failed = True

    # ------------------ LIFECYCLE -------------------------------------------

    @abstractmethod
    async def impl(self) -> None: ...
