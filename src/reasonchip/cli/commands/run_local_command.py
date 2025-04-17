# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import argparse
import re
import json
import logging

from reasonchip.core import exceptions as rex
from reasonchip.core.engine.context import Variables
from reasonchip.utils.local_runner import LocalRunner

from .exit_code import ExitCode
from .command import AsyncCommand

log = logging.getLogger(__name__)


class RunLocalCommand(AsyncCommand):

    @classmethod
    def command(cls) -> str:
        """
        Return the command name for this class.

        :return: Command string
        """
        return "run-local"

    @classmethod
    def help(cls) -> str:
        """
        Return brief help string for this command.

        :return: Help description string
        """
        return "Run a pipeline locally"

    @classmethod
    def description(cls) -> str:
        """
        Return extended description for this command.

        :return: Description string
        """
        return "Run a pipeline locally"

    @classmethod
    def build_parser(cls, parser: argparse.ArgumentParser):
        """
        Build the argument parser with command-specific options.

        :param parser: ArgumentParser instance to configure
        """
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
            help="Variable file to load into context",
        )

        cls.add_default_options(parser)

    async def main(
        self,
        args: argparse.Namespace,
        rem: typing.List[str],
    ) -> ExitCode:
        """
        Main entry point for running the local pipeline command.

        :param args: Parsed command line arguments
        :param rem: Remaining arguments after parsing

        :return: ExitCode indicating success or failure
        """

        if not args.collections:
            args.collections = ["."]

        try:
            # Load variables from files and key-value overrides
            variables = Variables()
            for x in args.vars:
                log.info(f"Loading variable file: {x}")
                variables.load_file(x)

            for x in args.set:
                m = re.match(r"^(.*?)=(.*)$", x)
                if not m:
                    raise ValueError(f"Invalid key value pair: {x}")

                key, value = m[1], m[2]
                log.info(f"Setting variable {key}={value}")
                variables.set(key, value)

            # Create the local runner with the specified collections and variables
            log.info(
                f"Creating LocalRunner with collections: {args.collections}"
            )
            runner = LocalRunner(
                collections=args.collections,
                default_variables=variables.vdict,
            )

            # Run the specified pipeline
            log.info(f"Running pipeline: {args.pipeline}")
            rc = await runner.run(args.pipeline)

            if rc:
                output = json.dumps(rc)
                print(output)
                log.info(f"Pipeline returned: {output}")

            # Shutdown the runner
            log.info("Shutting down LocalRunner")
            runner.shutdown()

            return ExitCode.OK

        except rex.ReasonChipException as ex:
            msg = rex.print_reasonchip_exception(ex)
            print(msg)
            log.error(f"ReasonChip exception occurred: {msg}")
            return ExitCode.ERROR

        except Exception as ex:
            print(f"************** UNHANDLED EXCEPTION **************")
            print(f"\n\n{type(ex)}\n\n")
            print(ex)
            log.error(f"Unhandled exception: {ex}", exc_info=True)
            return ExitCode.ERROR
