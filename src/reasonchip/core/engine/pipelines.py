# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

from __future__ import annotations

import os
import typing

from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    model_validator,
    field_validator,
)

import typing

from ruamel.yaml import YAML
from ruamel.yaml.parser import ParserError


from .. import exceptions as rex


# -------------------------- PARSING ----------------------------------------


def parse_task(t: typing.Union[Task, typing.Dict], task_no: int) -> Task:
    # Already parsed?
    if isinstance(t, Task):
        return t

    try:
        if "tasks" in t:
            return TaskSet.model_validate(t)

        if "dispatch" in t:
            return DispatchPipelineTask.model_validate(t)

        if "return" in t:
            return ReturnTask.model_validate(t)

        if "declare" in t:
            return DeclareTask.model_validate(t)

        if "comment" in t:
            return CommentTask.model_validate(t)

        if "terminate" in t:
            return TerminateTask.model_validate(t)

        if "chip" in t:
            return ChipTask.model_validate(t)

    except ValidationError as ve:
        raise rex.TaskParseException(
            message="Task failed to parse",
            task_no=task_no,
            errors=ve.errors(),
        )

    raise rex.TaskParseException(
        message="Unknown task type",
        task_no=task_no,
    )


# -------------------------- DIFFERENT TASKS --------------------------------


class TaskSet(BaseModel):
    name: typing.Optional[str] = None
    when: typing.Optional[str] = None
    variables: typing.Optional[typing.Dict[str, typing.Any]] = None

    run_async: bool = False

    tasks: typing.List[Task]

    store_result_as: typing.Optional[str] = None
    append_result_into: typing.Optional[str] = None

    loop: typing.Optional[typing.Union[str, typing.List]] = None

    class Config:
        extra = "forbid"

    @field_validator("tasks", mode="before")
    @classmethod
    def validate_tasks(
        cls, tasks: typing.List[typing.Any]
    ) -> typing.List[Task]:
        return [parse_task(t, i) for i, t in enumerate(tasks)]


class DispatchPipelineTask(BaseModel):
    name: typing.Optional[str] = None
    when: typing.Optional[str] = None
    variables: typing.Optional[typing.Dict[str, typing.Any]] = None

    run_async: bool = False

    dispatch: str

    store_result_as: typing.Optional[str] = None
    append_result_into: typing.Optional[str] = None

    loop: typing.Optional[typing.Union[str, typing.List]] = None

    class Config:
        extra = "forbid"


class ChipTask(BaseModel):
    name: typing.Optional[str] = None
    when: typing.Optional[str] = None
    variables: typing.Optional[typing.Dict[str, typing.Any]] = None

    run_async: bool = False

    chip: str
    params: typing.Any

    store_result_as: typing.Optional[str] = None
    append_result_into: typing.Optional[str] = None

    loop: typing.Optional[typing.Union[str, typing.List]] = None

    class Config:
        extra = "forbid"


class ReturnTask(BaseModel):
    name: typing.Optional[str] = None
    when: typing.Optional[str] = None
    result: typing.Any

    class Config:
        extra = "forbid"

    @model_validator(mode="before")
    @classmethod
    def map_return_value(cls, data: typing.Any) -> typing.Any:
        if not isinstance(data, dict):
            return data

        ignore_list = [
            "name",
            "when",
        ]

        method_keys = [key for key in data.keys() if key not in ignore_list]

        if len(method_keys) != 1:
            raise ValueError(f"You have to define a return value")

        assert method_keys[0] == "return"

        data["result"] = data.pop("return")
        return data


class DeclareTask(BaseModel):
    name: typing.Optional[str] = None
    when: typing.Optional[str] = None
    variables: typing.Optional[typing.Dict[str, typing.Any]] = None

    declare: typing.Dict[str, typing.Any]

    store_result_as: typing.Optional[str] = None
    append_result_into: typing.Optional[str] = None

    loop: typing.Optional[typing.Union[str, typing.List]] = None

    class Config:
        extra = "forbid"


class CommentTask(BaseModel):
    name: typing.Optional[str] = None
    comment: typing.Any

    class Config:
        extra = "forbid"


class TerminateTask(BaseModel):
    name: typing.Optional[str] = None
    when: typing.Optional[str] = None

    terminate: typing.Any

    class Config:
        extra = "forbid"


# -------------------------- TYPES AND THE PIPELINE -------------------------

Task = typing.Union[
    TaskSet,
    DispatchPipelineTask,
    ChipTask,
    ReturnTask,
    DeclareTask,
    CommentTask,
    TerminateTask,
]

SaveableTask = typing.Union[
    TaskSet, DispatchPipelineTask, DeclareTask, ChipTask
]
LoopableTask = typing.Union[
    TaskSet, DispatchPipelineTask, DeclareTask, ChipTask
]


class Pipeline(BaseModel):
    tasks: typing.List[Task] = Field(default_factory=list)

    class Config:
        extra = "forbid"

    @field_validator("tasks", mode="before")
    @classmethod
    def validate_tasks(
        cls, tasks: typing.List[typing.Any]
    ) -> typing.List[Task]:
        return [parse_task(t, i) for i, t in enumerate(tasks)]


PipelineSetType = typing.Dict[str, Pipeline]


# -------------------------- LOADER -----------------------------------------


class PipelineLoader:
    """
    Loads the pipeline collections from the given path.
    """

    def __init__(self):
        """
        Constructor.
        """
        self._yaml: YAML = YAML()

    def load_from_tree(self, path: str) -> PipelineSetType:
        """
        Load all pipelines from the given path.

        Anything with a .yml extension is considered a pipeline file.

        :param path: Path to the directory containing the pipelines.

        :return: A dict of pipelines by name.
        """
        try:
            pips: PipelineSetType = {}

            # For every file in the tree, load it and add it to the collections
            tree = self.traverse_tree(path)
            for t in tree:
                # Load the file into the collection
                pip = self.load_from_file(os.path.join(path, t))
                if pip:
                    # We store by route
                    name = t.replace(".yml", "").replace("/", ".")
                    pips[name] = pip

            # Return all collections
            return pips

        except rex.ParsingException as ex:
            ex.source = f"{path}/{ex.source}"
            raise

    def load_from_file(self, filename: str) -> typing.Optional[Pipeline]:
        """
        Load pipeline from the file.

        :param filename: Filename of the pipeline file.

        :return: Pipeline or None if the content is pointless.
        """
        # Load the file into the collection
        try:
            with open(filename, "r") as f:
                contents = f.read()

            return self.load_from_string(contents)

        except FileNotFoundError:
            raise rex.ParsingException(source=f"{filename} (not found)")

        except PermissionError:
            raise rex.ParsingException(source=f"{filename} (permission denied)")

        except IsADirectoryError:
            raise rex.ParsingException(source=f"{filename} (is a directory)")

        except rex.PipelineFormatException as ex:
            raise rex.ParsingException(source=filename) from ex

    def load_from_string(
        self,
        content: str,
    ) -> typing.Optional[Pipeline]:
        """
        Load and process all the tasks in the content.

        :param content: String containing the pipeline tasks.

        :return: Pipeline or None if the content is pointless.
        """
        try:
            tasks = self._yaml.load(content)
            if not tasks:
                # Pipeline file is empty
                return

            if not isinstance(tasks, list):
                # Pipeline file is not a list of tasks
                raise rex.PipelineFormatException(
                    message="Pipeline file must be a list of tasks"
                )

            pipeline = Pipeline.model_validate(
                {"tasks": [parse_task(t, i) for i, t in enumerate(tasks)]}
            )
            return pipeline

        except ParserError as ex:
            resp = f"Error parsing YAML\n\n{ex}"
            raise rex.PipelineFormatException(message=resp)

        except rex.TaskParseException as ex:
            raise rex.PipelineFormatException(
                message="There were issues parsing the tasks"
            ) from ex

    # ---------------- FILE AND TREE PROCESSING ------------------------------

    def traverse_tree(self, path: str) -> typing.List[str]:
        """
        Finds all files with a .yml extension in the given path.

        :param path: Path to the root directory to traverse.

        :return: List of found files relative to path.
        """
        yml_files = []
        for root, _, files in os.walk(path):
            for file in files:
                # Make sure it doesn't start with underscore
                if file.startswith(("_",)):
                    continue

                if file.endswith((".yml",)):
                    full_path = os.path.relpath(os.path.join(root, file), path)
                    yml_files.append(full_path)
        return yml_files
