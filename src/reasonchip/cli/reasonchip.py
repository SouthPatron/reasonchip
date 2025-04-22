# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import sys
import argparse
import asyncio
import setproctitle

from ..core.logging.configure import configure_logging

from .commands import get_commands, AsyncCommand, ExitCode


def main() -> ExitCode:
    """
    Main entry point for the program.
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
        return ExitCode.OK

    # Create the objects
    myargs, remaining = parser.parse_known_args(sys.argv[1:])

    # Set up logging
    configure_logging(myargs.log_levels)

    # Get the command and change process names
    obj = commands[myargs.subcommand]()

    setproctitle.setproctitle(myargs.subcommand)

    # Dispatch appropriately
    if isinstance(obj, AsyncCommand):
        rc = asyncio.run(obj.main(myargs, remaining))
    else:
        rc = obj.main(myargs, remaining)

    # ... and return it.
    return rc
