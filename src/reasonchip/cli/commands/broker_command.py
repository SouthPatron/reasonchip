# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import argparse
import asyncio
import signal
import traceback

from reasonchip.core import exceptions as rex
from reasonchip.net.broker import Broker
from reasonchip.net.transports import SSLServerOptions

from reasonchip.net.protocol import DEFAULT_SERVERS, DEFAULT_LISTENERS
from reasonchip.net.transports.utils import (
    broker_for_workers,
    broker_for_clients,
    SSLServerOptions,
)


from .exit_code import ExitCode
from .command import AsyncCommand


class BrokerCommand(AsyncCommand):

    def __init__(self):
        super().__init__()
        self._die: asyncio.Event = asyncio.Event()

    @classmethod
    def command(cls) -> str:
        return "broker"

    @classmethod
    def help(cls) -> str:
        return "Starts a broker to dispatch tasks to engines"

    @classmethod
    def description(cls) -> str:
        return """
Run a broker for mediation between engines and the clients.

Engines connect to the broker and register for work.
Clients connect to a broker and submit work to be done.
The work in this case is the running of pipelines.

Make sure to spawn multiple engines to connect to the broker. If you don't
have engines, nothing can happen.

This can listen on multiple sockets, IP4, and IP6 addresses.
"""

    @classmethod
    def build_parser(cls, parser: argparse.ArgumentParser):
        parser.add_argument(
            "--listen",
            action="append",
            metavar="<path or ip address>",
            default=[],
            help="Listen for workers on this endpoint",
        )
        parser.add_argument(
            "--serve",
            action="append",
            metavar="<path or ip address>",
            default=[],
            help="Serve clients on this endpoint",
        )

        cls.add_default_options(parser)
        cls.add_ssl_server_options(parser)

    async def main(
        self,
        args: argparse.Namespace,
        rem: typing.List[str],
    ) -> ExitCode:
        """
        Main entry point for the application.
        """

        ssl_options = SSLServerOptions.from_args(args)
        ssl_context = ssl_options.create_ssl_context() if ssl_options else None

        listeners = broker_for_workers(
            args.listen or DEFAULT_LISTENERS,
            ssl_server_options=ssl_options,
            ssl_context=ssl_context,
        )
        servers = broker_for_clients(args.serve or DEFAULT_SERVERS)

        await self.setup_signal_handlers()

        try:

            broker = Broker(
                client_transports=servers,
                worker_transports=listeners,
            )

            await broker.start()

            await self._wait_for_exit()

            await broker.stop()

            return ExitCode.OK

        except rex.ReasonChipException as ex:
            msg = rex.print_reasonchip_exception(ex)
            print(msg)
            return ExitCode.ERROR

        except Exception as ex:
            print(f"************** UNHANDLED EXCEPTION **************")
            print(f"\n\n{ex}\n\n")
            traceback.print_exc()
            return ExitCode.ERROR

    async def _wait_for_exit(self) -> None:
        await self._die.wait()

    async def _handle_signal(self, signame: str) -> None:
        self._die.set()

    async def setup_signal_handlers(self):
        loop = asyncio.get_event_loop()
        for signame in {"SIGINT", "SIGTERM", "SIGHUP"}:
            loop.add_signal_handler(
                getattr(signal, signame),
                lambda: asyncio.create_task(self._handle_signal(signame)),
            )
