import typing
import asyncio

from collections import defaultdict

from dataclasses import dataclass


@dataclass
class StackFrame:
    pipeline: str
    task_no: int


class Stack:

    def __init__(self):
        self._frames: typing.Dict[int, typing.List[StackFrame]] = defaultdict(
            list
        )

    def push(self, pipeline: str):
        t = asyncio.current_task()

        task_id = id(t)

        self._frames[task_id].append(
            StackFrame(
                pipeline=pipeline,
                task_no=0,
            )
        )

    def pop(self):
        t = asyncio.current_task()

        task_id = id(t)

        assert task_id in self._frames

        self._frames[task_id].pop()
        if not self._frames[task_id]:
            del self._frames[task_id]

    def tick(self):
        t = asyncio.current_task()

        task_id = id(t)

        assert task_id in self._frames

        self._frames[task_id][-1].task_no += 1

    def clear(self):
        t = asyncio.current_task()

        task_id = id(t)

        assert task_id in self._frames

        del self._frames[task_id]

    def clear_all(self):
        self._frames.clear()
