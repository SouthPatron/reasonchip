# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import argparse
import re
import json

from reasonchip.core import exceptions as rex
from reasonchip.core.engine.variables import Variables
from reasonchip.utils.local_runner import LocalRunner

from .exit_code import ExitCode
from .command import AsyncCommand


class RunLocalCommand(AsyncCommand):

    @classmethod
    def command(cls) -> str:
        return "run-local"

    @classmethod
    def help(cls) -> str:
        return "Run a pipeline locally"

    @classmethod
    def description(cls) -> str:
        return "Run a pipeline locally"

    @classmethod
    def build_parser(cls, parser: argparse.ArgumentParser):
        parser.add_argument(
            "pipeline",
            metavar="<name>",
            type=str,
            help="Name of the pipeline to run",
        )
        parser.add_argument(
            "--collection",
            dest="collections",
            action="append",
            default=[],
            metavar="<collection root>",
            type=str,
            help="Root of a pipeline collection",
        )
        parser.add_argument(
            "--set",
            action="append",
            default=[],
            metavar="key=value",
            type=str,
            help="Set or override a configuration key-value pair.",
        )
        parser.add_argument(
            "--vars",
            action="append",
            default=[],
            metavar="<variable file>",
            type=str,
            help="Variable file to load",
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

        try:
            # Load variables
            variables = Variables()
            for x in args.vars:
                variables.load_file(x)

            for x in args.set:
                m = re.match(r"^(.*?)=(.*)$", x)
                if not m:
                    raise ValueError(f"Invalid key value pair: {x}")

                key, value = m[1], m[2]
                variables.set(key, value)

            # Create the local runner
            runner = LocalRunner(
                collections=args.collections,
                default_variables=variables.vdict,
            )

            # Run the engine
            rc = await runner.run(args.pipeline)

            if rc:
                print(json.dumps(rc))

            # Shutdown the engine
            runner.shutdown()

            return ExitCode.OK

        except rex.ReasonChipException as ex:
            msg = rex.print_reasonchip_exception(ex)
            print(msg)
            return ExitCode.ERROR

        except Exception as ex:
            print(f"************** UNHANDLED EXCEPTION **************")
            print(f"\n\n{type(ex)}\n\n")
            print(ex)
            return ExitCode.ERROR
