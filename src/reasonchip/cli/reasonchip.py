#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import sys
import argparse
import asyncio
import setproctitle
import logging

from ..core.logging.configure import configure_logging

from .commands import get_commands, AsyncCommand, ExitCode

log = logging.getLogger(__name__)


def main() -> ExitCode:
    """
    Main entry point for the program.

    This function parses command line arguments, configures logging,
    sets the process title, and dispatches to the selected subcommand.

    :return: The exit code resulting from running the selected subcommand.
    """
    # Build the argument tree
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Open source agentic workflow automation software",
        add_help=False,
    )

    subparsers = parser.add_subparsers(
        dest="subcommand",
        metavar="<subcommand>",
        required=True,
    )

    # Let all the commands build their own parser
    commands = get_commands()
    for cmd, obj in commands.items():
        tmp = subparsers.add_parser(
            cmd,
            help=obj.help(),
            description=obj.description(),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        obj.build_parser(tmp)

    # If there are no arguments, print the help
    if len(sys.argv) == 1:
        parser.print_help()
        log.info("No arguments provided; help message displayed.")
        return ExitCode.OK

    # Create the objects
    myargs, remaining = parser.parse_known_args(sys.argv[1:])

    # Set up logging based on parsed arguments
    configure_logging(myargs.log_levels)
    log.info(f"Logging configured with levels: {myargs.log_levels}")

    # Get the command and change process names
    obj = commands[myargs.subcommand]()

    setproctitle.setproctitle(myargs.subcommand)
    log.info(f"Process title set to: {myargs.subcommand}")

    # Dispatch appropriately based on command type
    if isinstance(obj, AsyncCommand):
        log.info(f"Running async command: {myargs.subcommand}")
        rc = asyncio.run(obj.main(myargs, remaining))
    else:
        log.info(f"Running command: {myargs.subcommand}")
        rc = obj.main(myargs, remaining)

    # Log the return code and return it
    log.info(f"Command {myargs.subcommand} exited with code: {rc}")
    return rc
