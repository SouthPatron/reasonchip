# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.


import typing

from ..core.engine.engine import Engine
from ..core.engine.variables import Variables


class LocalRunner:

    def __init__(
        self,
        collections: typing.List[str],
        default_variables: typing.Dict[str, typing.Any] = {},
    ):
        # Create the engine
        self._engine: Engine = Engine()
        self._engine.initialize(pipelines=collections)

        # Create the variables
        self._default_variables: Variables = Variables(default_variables)

    async def run(
        self,
        pipeline: str,
        variables: typing.Dict[str, typing.Any] = {},
    ) -> typing.Any:

        # Create the variables
        new_vars = self._default_variables.copy()
        new_vars.update(variables)

        # Run the engine
        return await self._engine.run(pipeline, new_vars)

    def shutdown(self):
        self._engine.shutdown()
