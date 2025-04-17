# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.


import typing
import logging

from ..core.engine.engine import Engine
from ..core.engine.context import Variables

log = logging.getLogger(__name__)


class LocalRunner:

    def __init__(
        self,
        collections: typing.List[str],
        default_variables: typing.Dict[str, typing.Any] = {},
    ):
        """
        Initialize LocalRunner with pipeline collections and default variables.

        :param collections: List of pipeline collection names.
        :param default_variables: Default variables to be used during pipeline runs.
        """
        # Create the engine
        self._engine: Engine = Engine()
        self._engine.initialize(pipelines=collections)
        log.info(f"Engine initialized with pipelines: {collections}")

        # Create the variables
        self._default_variables: Variables = Variables(default_variables)
        log.info(f"Default variables set: {default_variables}")

    async def run(
        self,
        pipeline: str,
        variables: typing.Dict[str, typing.Any] = {},
    ) -> typing.Any:
        """
        Run the specified pipeline with provided variables.

        :param pipeline: The name of the pipeline to run.
        :param variables: Variables to override defaults for this run.

        :return: Result of the pipeline execution.
        """

        # Create the variables
        new_vars = self._default_variables.copy()
        new_vars.update(variables)
        log.info(f"Running pipeline '{pipeline}' with variables: {variables}")

        # Run the engine
        result = await self._engine.run(pipeline, new_vars)
        log.info(f"Pipeline '{pipeline}' executed with result: {result}")
        return result

    def shutdown(self):
        """
        Shutdown the engine instance.
        """
        self._engine.shutdown()
        log.info("Engine shutdown complete.")
