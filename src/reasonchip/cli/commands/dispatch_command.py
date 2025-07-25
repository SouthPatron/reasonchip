# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import argparse
import re
import json
import uuid
import logging
import traceback

from .exit_code import ExitCode
from .command import AsyncCommand

log = logging.getLogger("reasonchip.cli.commands.dispatch")


class DispatchCommand(AsyncCommand):

    @classmethod
    def command(cls) -> str:
        return "dispatch"

    @classmethod
    def help(cls) -> str:
        return "Dispatch a workflow"

    @classmethod
    def description(cls) -> str:
        return """
This dispatches a workflow with variables to the AMQP broker.
"""

    @classmethod
    def build_parser(cls, parser: argparse.ArgumentParser):
        parser.add_argument(
            "workflow",
            metavar="<name>",
            type=str,
            help="Name of the workflow to run",
        )
        parser.add_argument(
            "--variables",
            action="append",
            default=[],
            metavar="<variable file>",
            type=str,
            help="Variable file to load. Successive files will be merged.",
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
            "--cookie",
            action="store",
            metavar="<UUID>",
            default=None,
            type=uuid.UUID,
            help="Cookie to use (defaults to a random UUID)",
        )

        cls.add_default_options(parser)
        cls.add_amqp_options(parser)

    async def main(
        self,
        args: argparse.Namespace,
        rem: typing.List[str],
    ) -> ExitCode:
        """
        Main entry point for the application.
        """
        # Populate the default variables to be sent through
        variables: typing.Dict = {}

        # Load variables
        for v in args.variables:
            with open(v, "r") as f:
                new_vars = json.loads(f.read())
                variables = self._deep_merge(variables, new_vars)

        for x in args.set:
            m = re.match(r"^(.*?)=(.*)$", x)
            if not m:
                raise ValueError(f"Invalid key value pair: {x}")

            key, value = m[1], m[2]
            variables = self._deep_update(variables, key, value)

        # Create the connection
        try:
            from pprint import pprint

            pprint(variables)

        except Exception as ex:
            print("************** EXCEPTION ************************")
            traceback.print_exc()

        return ExitCode.OK

    # -------------------------- VARIABLES -----------------------------------

    def _deep_merge(
        self,
        orig_dict: typing.Dict,
        new_dict: typing.Dict,
    ) -> typing.Dict:
        result: typing.Dict[str, typing.Any] = {}

        keys = set(orig_dict) | set(new_dict)
        for key in keys:
            base_val = orig_dict.get(key)
            update_val = new_dict.get(key)

            if isinstance(base_val, dict) and isinstance(update_val, dict):
                result[key] = self._deep_merge(base_val, update_val)
            elif key in new_dict:
                result[key] = update_val
            else:
                result[key] = base_val

        return result

    def _deep_update(
        self,
        orig_dict: typing.Dict,
        key: str,
        value: typing.Any,
    ) -> typing.Dict:

        # Create a dict to generate
        new_dict = {}

        keys = key.split(".")

        current = new_dict
        for k in keys[:-1]:
            current[k] = {}
            current = current[k]

        current[keys[-1]] = value
        return self._deep_merge(orig_dict, new_dict)
