# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import argparse
import signal
import asyncio
import traceback
import ssl

from reasonchip.core import exceptions as rex
from reasonchip.core.engine.engine import Engine
from reasonchip.net.worker import TaskManager

from reasonchip.net.protocol import DEFAULT_LISTENERS
from reasonchip.net.transports import worker_to_broker
from reasonchip.net.transports import SSLClientOptions


from .exit_code import ExitCode
from .command import AsyncCommand


class WorkerCommand(AsyncCommand):

    def __init__(self):
        super().__init__()
        self._die = asyncio.Event()

    @classmethod
    def command(cls) -> str:
        return "worker"

    @classmethod
    def help(cls) -> str:
        return "Launch an engine process to perform work for a broker"

    @classmethod
    def description(cls) -> str:
        return """
This is an engine process which provides workers to a broker. This process isn't meant to be used directly. It registers the number of tasks available with the broker and the broker dispatches tasks to this engine up to that capacity.

You may specify how many parallel tasks may be executed at any one time.

The broker address should be specified like these examples:

  socket:///tmp/reasonchip.serve
  tcp://0.0.0.0/
  tcp://127.0.0.1:51501/
  tcp://[::1]:51501/
  tcp://[::]/

The default connection port is 51501.

Unless specified, the default broker is:

  socket:///tmp/reasonchip-broker-engine.sock

It's an incredibly intolerant process by design. It will die if anything strange happens between it and the broker. The broker should know what it's doing.
"""

    @classmethod
    def build_parser(cls, parser: argparse.ArgumentParser):
        parser.add_argument(
            "--collection",
            dest="collections",
            action="append",
            default=[],
            metavar="<directory>",
            type=str,
            help="Root path of a pipeline collection. Default serves ./ only",
        )
        parser.add_argument(
            "--broker",
            metavar="<address>",
            type=str,
            default=DEFAULT_LISTENERS[0],
            help="Address of the broker. Socket or IP4/6",
        )
        parser.add_argument(
            "--tasks",
            metavar="<number>",
            type=int,
            default=4,
            help="The number of tasks to run in parallel",
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

        if not args.collections:
            args.collections = ["."]

        ssl_options = SSLClientOptions.from_args(args)
        ssl_context = ssl_options.create_ssl_context() if ssl_options else None

        # Let's create the SSL context right up front.
        transport = worker_to_broker(
            args.broker,
            ssl_client_options=ssl_options,
            ssl_context=ssl_context,
        )

        await self.setup_signal_handlers()

        try:
            # Let us create the engine.
            engine: Engine = Engine()
            engine.initialize(pipelines=args.collections)

            # Now we start the loop to receive requests and process them.
            tm = TaskManager(
                engine=engine,
                transport=transport,
                max_capacity=args.tasks,
            )
            await tm.start()

            # Wait for signals or the client to stop
            task_wait = asyncio.create_task(self._die.wait())
            task_manager = asyncio.create_task(tm.wait())

            wl = [task_wait, task_manager]

            while wl:
                done, _ = await asyncio.wait(
                    wl,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if task_wait in done:
                    wl.remove(task_wait)
                    task_wait = None

                    if task_manager in wl:
                        await tm.stop()

                if task_manager in done:
                    wl.remove(task_manager)
                    task_manager = None

                    if task_wait in wl:
                        self._die.set()

            # Shutdown the engine
            engine.shutdown()
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

    async def _handle_signal(self, signame: str) -> None:
        self._die.set()

    async def setup_signal_handlers(self):
        loop = asyncio.get_event_loop()
        for signame in {"SIGINT", "SIGTERM", "SIGHUP"}:
            loop.add_signal_handler(
                getattr(signal, signame),
                lambda: asyncio.create_task(self._handle_signal(signame)),
            )
