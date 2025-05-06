# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.import typing

import typing
import asyncio

from io import StringIO

from pydantic import BaseModel
from ruamel.yaml import YAML

from collections import defaultdict

from dataclasses import dataclass


@dataclass
class StackFrame:
    pipeline: str
    task_no: int
    task: typing.Optional[BaseModel] = None


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
                task=None,
            )
        )

    def pop(self):
        t = asyncio.current_task()

        task_id = id(t)

        assert task_id in self._frames

        self._frames[task_id].pop()
        if not self._frames[task_id]:
            del self._frames[task_id]

    def tick(self, task: BaseModel):
        t = asyncio.current_task()

        task_id = id(t)

        assert task_id in self._frames

        self._frames[task_id][-1].task_no += 1
        self._frames[task_id][-1].task = task

    def clear(self):
        t = asyncio.current_task()

        task_id = id(t)

        assert task_id in self._frames

        del self._frames[task_id]

    def clear_all(self):
        self._frames.clear()

    def print(self):
        lines = self.as_list()
        for l in lines:
            print(l)

    def as_list(self) -> typing.List[str]:
        rc = []

        if not self._frames:
            return rc

        yaml = YAML()
        yaml.indent(sequence=2, offset=2)

        rc.append("Processor Stack Trace:")

        for t in self._frames:
            rc.append(f"  Task ID: {t}")

            max_tasks = len(self._frames[t])

            for i, frame in enumerate(self._frames[t]):
                indent = " " * ((i + 2) * 2)
                rc.append(f"{indent}{frame.pipeline} - {frame.task_no}")

                if i < max_tasks - 1:
                    continue

                task = frame.task

                # Dump to a string
                if task:
                    obj = {"task": task.model_dump()}

                    stream = StringIO()
                    yaml.dump(obj, stream)

                    yaml_str = stream.getvalue()

                    # Indented YAML
                    indented_yaml = "\n".join(
                        indent + line for line in yaml_str.splitlines()
                    )
                    rc.append(f"\n{indent}--- TASK ---")
                    rc.append(indented_yaml)
                    rc.append(f"{indent}------------")

        return rc
