# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import argparse
import re
import json
import traceback

from pathlib import Path

from reasonchip.core import exceptions as rex
from reasonchip.core.engine.workflows import WorkflowLoader
from reasonchip.core.engine.engine import (
    Engine,
    EngineContext,
    WorkflowSet,
)

from .exit_code import ExitCode
from .command import AsyncCommand


class RunLocalCommand(AsyncCommand):

    @classmethod
    def command(cls) -> str:
        return "run-local"

    @classmethod
    def help(cls) -> str:
        return "Run a workflow locally"

    @classmethod
    def description(cls) -> str:
        return "Run a workflow locally"

    @classmethod
    def build_parser(cls, parser: argparse.ArgumentParser):
        parser.add_argument(
            "workflow",
            metavar="<name>",
            type=str,
            help="Name of the workflow to run",
        )
        parser.add_argument(
            "--collection",
            dest="collections",
            action="append",
            default=[],
            metavar="name=<root>",
            type=str,
            help="Root of a workflow collection",
        )

        cls.add_default_options(parser)

    async def main(
        self,
        args: argparse.Namespace,
        rem: typing.List[str],
    ) -> ExitCode:
        """
        Main entry point for the application.
        """

        if not args.collections:
            args.collections = ["."]

        workflow_loader = WorkflowLoader()

        workflow_set = WorkflowSet()

        try:
            # Create the WorkflowSet
            for x in args.collections:
                m = re.match(r"^(.*?)=(.*)$", x)
                if not m:
                    raise ValueError(f"Invalid key value pair: {x}")

                key, value = m[1], m[2]

                abs_path = str(Path(value).resolve())

                workflow = workflow_loader.load_from_path(
                    module_name=key,
                    path=abs_path,
                )

                workflow_set.add(workflow)

            # Create the Engine and EngineContext
            context = EngineContext(workflow_set=workflow_set)
            engine = Engine(workflow_set=workflow_set)

            # Run the engine and the run
            rc = await engine.run(
                context=context,
                entry=args.workflow,
            )
            if rc:
                print(json.dumps(rc))

            # Shutdown the engine
            return ExitCode.OK

        except rex.EngineException as ex:
            print(f"************** ENGINE EXCEPTION *****************")

            traceback.print_exc()

            return ExitCode.ERROR

        except Exception as ex:
            print(f"************** UNHANDLED EXCEPTION **************")

            traceback.print_exc()

            return ExitCode.ERROR
