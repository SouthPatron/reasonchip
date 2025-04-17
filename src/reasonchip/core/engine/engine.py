# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import logging

from .pipelines import (
    PipelineLoader,
    Pipeline,
    Task,
    TaskSet,
    DispatchPipelineTask,
    ChipTask,
)
from .processor.processor import Processor
from .context import Variables, FlowControl
from .registry import Registry

from .. import exceptions as rex

log = logging.getLogger(__name__)


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
        """
        Property to access loaded pipelines.

        :return: Dictionary of pipeline name keys to Pipeline objects.
        """
        return self._pipelines

    def initialize(
        self,
        pipelines: typing.List[str],
    ):
        """
        Load all pipelines and chips.

        :param pipelines: List of paths to the pipeline collection roots.
        """
        log.info("Initializing engine with pipeline roots: %s", pipelines)

        # Load all the collections
        loader = PipelineLoader()
        for r in pipelines:
            col = loader.load_from_tree(r)
            self._pipelines.update(col)
            log.info("Loaded pipeline collection from: %s", r)

        self._validate()
        log.info(
            "Engine initialization complete with %d pipelines loaded",
            len(self._pipelines),
        )

    def shutdown(self):
        """
        Clean up and shutdown the engine.
        """
        log.info("Engine shutdown called")
        pass

    async def run(
        self,
        entry: str,
        variables: Variables,
    ) -> typing.Any:
        """
        Run a pipeline entry point asynchronously.

        :param entry: The name of the pipeline to run.
        :param variables: Variables context for execution.

        :return: The result of the pipeline processing.
        """

        async def get_pipeline(name: str) -> typing.Optional[Pipeline]:
            log.debug("Resolving pipeline: %s", name)
            return self._pipelines.get(name, None)

        pipeline = await get_pipeline(entry)
        if not pipeline:
            log.error("No such pipeline found: %s", entry)
            raise rex.NoSuchPipelineException(entry)

        flow = FlowControl(flow=pipeline.tasks)
        log.debug("Created flow control for pipeline tasks")

        processor = Processor(resolver=get_pipeline)
        log.info("Starting pipeline processing: %s", entry)

        result = await processor.run(
            variables=variables,
            flow=flow,
        )

        log.info("Completed pipeline processing: %s", entry)
        return result

    # -------------- VALIDATION --------------------------------------------

    def _validate(self):
        """
        Validates the pipeline collections, as much as possible.
        """
        log.info("Starting pipeline validation")

        for name, pipeline in self._pipelines.items():

            def check_tasks(tasks: typing.List[Task]):
                for i, t in enumerate(tasks):
                    if isinstance(t, DispatchPipelineTask):
                        # Check for the pipeline existence
                        pipeline_name = t.dispatch
                        log.debug(
                            "Validating DispatchPipelineTask task_no %d dispatching to: %s",
                            i,
                            pipeline_name,
                        )
                        if pipeline_name not in self._pipelines:
                            log.error(
                                "No such pipeline during validation: %s at task %d",
                                pipeline_name,
                                i,
                            )
                            raise rex.NoSuchPipelineDuringValidationException(
                                task_no=i,
                                pipeline=pipeline_name,
                            )

                    elif isinstance(t, ChipTask):
                        # Check for the chip existence
                        log.debug(
                            "Validating ChipTask task_no %d for chip: %s",
                            i,
                            t.chip,
                        )
                        chip = Registry.get_chip(t.chip)
                        if chip is None:
                            log.error(
                                "No such chip during validation: %s at task %d",
                                t.chip,
                                i,
                            )
                            raise rex.NoSuchChipDuringValidationException(
                                task_no=i,
                                chip=t.chip,
                            )

                    elif isinstance(t, TaskSet):
                        # We need to deep-dive a TaskSet
                        log.debug("Validating nested TaskSet task_no %d", i)
                        try:
                            check_tasks(t.tasks)
                        except rex.ValidationException as ex:
                            log.error(
                                "Nested validation exception at task %d", i
                            )
                            raise rex.NestedValidationException(
                                task_no=i,
                            ) from ex

                    else:
                        continue

            try:
                check_tasks(pipeline.tasks)
            except rex.ValidationException as ex:
                log.error("Validation exception in pipeline '%s'", name)
                raise rex.ValidationException(source=name) from ex

        log.info("Pipeline validation completed successfully")
