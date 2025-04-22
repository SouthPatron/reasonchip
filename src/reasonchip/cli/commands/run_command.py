# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import argparse
import re
import json

from reasonchip.core.engine.variables import Variables

from reasonchip.net.client import Multiplexor, Api
from reasonchip.net.protocol import DEFAULT_SERVERS
from reasonchip.net.transports import client_to_broker, SSLClientOptions

from .exit_code import ExitCode
from .command import AsyncCommand


class RunCommand(AsyncCommand):

    @classmethod
    def command(cls) -> str:
        return "run"

    @classmethod
    def help(cls) -> str:
        return "Run a pipeline"

    @classmethod
    def description(cls) -> str:
        return """
This command connects to a remote ReasonChip broker and runs a single
pipeline. You may specify variables on the command line.
"""

    @classmethod
    def build_parser(cls, parser: argparse.ArgumentParser):
        parser.add_argument(
            "pipeline",
            metavar="<name>",
            type=str,
            help="Name of the pipeline to run",
        )
        parser.add_argument(
            "--broker",
            metavar="<address>",
            type=str,
            default=DEFAULT_SERVERS[0],
            help="Address of the broker. Socket or IP4/6",
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
        cls.add_ssl_client_options(parser)

    async def main(
        self,
        args: argparse.Namespace,
        rem: typing.List[str],
    ) -> ExitCode:
        """
        Main entry point for the application.
        """
        # Populate the default variables to be sent through
        variables = Variables()

        # Load variables
        for x in args.vars:
            variables.load_file(x)

        for x in args.set:
            m = re.match(r"^(.*?)=(.*)$", x)
            if not m:
                raise ValueError(f"Invalid key value pair: {x}")

            key, value = m[1], m[2]
            variables.set(key, value)

        # Create the connection
        ssl_options = SSLClientOptions.from_args(args)
        ssl_context = ssl_options.create_ssl_context() if ssl_options else None

        transport = client_to_broker(
            args.broker,
            ssl_client_options=ssl_options,
            ssl_context=ssl_context,
        )

        # Create the Multiplexor
        multiplexor = Multiplexor(transport)

        rc = await multiplexor.start()
        if rc is False:
            raise ConnectionError("Could not connect to broker")

        # Get the API helper class
        api = Api(multiplexor)

        resp = await api.run_pipeline(
            pipeline=args.pipeline,
            variables=variables.vdict,
        )

        if resp:
            print(json.dumps(resp))

        await multiplexor.stop()

        return ExitCode.OK
