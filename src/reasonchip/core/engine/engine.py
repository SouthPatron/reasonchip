# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing

from .pipelines import (
    PipelineLoader,
    Pipeline,
    Task,
    TaskSet,
    DispatchPipelineTask,
    ChipTask,
)
from .processor import Processor
from .variables import Variables
from .flow_control import FlowControl
from .registry import Registry

from .. import exceptions as rex


class Engine:
    """
    A class with a big name and a little job.
    """

    def __init__(self):
        """
        Constructor.
        """
        self._pipelines: typing.Dict[str, Pipeline] = {}

    @property
    def pipelines(self) -> typing.Dict[str, Pipeline]:
        return self._pipelines

    def initialize(
        self,
        pipelines: typing.List[str],
    ):
        """
        Load all pipelines and chips.

        :param pipelines: List of paths to the pipeline collection roots.
        """
        # Load all the collections
        loader = PipelineLoader()
        for r in pipelines:
            col = loader.load_from_tree(r)
            self._pipelines.update(col)

        self._validate()

    def shutdown(self):
        pass

    async def run(
        self,
        entry: str,
        variables: Variables,
    ) -> typing.Any:

        async def get_pipeline(name: str) -> typing.Optional[Pipeline]:
            return self._pipelines.get(name, None)

        pipeline = await get_pipeline(entry)
        if not pipeline:
            raise rex.NoSuchPipelineException(entry)

        flow = FlowControl(flow=pipeline.tasks)

        processor = Processor(resolver=get_pipeline)

        return await processor.run(
            variables=variables,
            flow=flow,
        )

    # -------------- VALIDATION --------------------------------------------

    def _validate(self):
        """Validates the pipeline collections, as much as possible."""

        for name, pipeline in self._pipelines.items():

            def check_tasks(tasks: typing.List[Task]):
                for i, t in enumerate(tasks):
                    if isinstance(t, DispatchPipelineTask):
                        # Check for the pipeline existence
                        pipeline_name = t.dispatch
                        if pipeline_name not in self._pipelines:
                            raise rex.NoSuchPipelineDuringValidationException(
                                task_no=i,
                                pipeline=pipeline_name,
                            )

                    elif isinstance(t, ChipTask):
                        # Check for the chip existence
                        chip = Registry.get_chip(t.chip)
                        if chip is None:
                            raise rex.NoSuchChipDuringValidationException(
                                task_no=i,
                                chip=t.chip,
                            )

                    elif isinstance(t, TaskSet):
                        # We need to deep-dive a TaskSet
                        try:
                            check_tasks(t.tasks)
                        except rex.ValidationException as ex:
                            raise rex.NestedValidationException(
                                task_no=i,
                            ) from ex

                    else:
                        continue

            try:
                check_tasks(pipeline.tasks)
            except rex.ValidationException as ex:
                raise rex.ValidationException(source=name) from ex
