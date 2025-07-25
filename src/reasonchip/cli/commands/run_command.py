# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import argparse
import re
import json
import logging
import traceback

from pathlib import Path

from reasonchip.core.engine.workflows import WorkflowLoader
from reasonchip.core.engine.engine import Engine, WorkflowSet

from .exit_code import ExitCode
from .command import AsyncCommand


log = logging.getLogger("reasonchip.cli.commands.run")


class RunCommand(AsyncCommand):

    @classmethod
    def command(cls) -> str:
        return "run"

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
            metavar="name=<directory>",
            type=str,
            help="Root of a workflow collection",
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

        cls.add_default_options(parser)

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

        workflow_loader = WorkflowLoader()
        workflow_set = WorkflowSet()

        try:
            # Create the WorkflowSet.
            log.info(f"Attempting to load {len(args.collections)} collections")
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

                log.info(f"\tLoaded workflow '{key}' from {abs_path}")

            # Create the Engine and EngineContext
            engine = Engine(workflow_set=workflow_set)

            # Run the engine and the run
            rc = await engine.run(entry=args.workflow, **variables)
            if rc:
                print(json.dumps(rc))

            # Shutdown the engine
            return ExitCode.OK

        except Exception:
            print(f"************** UNHANDLED EXCEPTION **************")

            traceback.print_exc()

            return ExitCode.ERROR

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
