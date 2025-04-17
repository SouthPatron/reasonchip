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
import logging

from reasonchip.core import exceptions as rex
from reasonchip.core.engine.engine import Engine
from reasonchip.net.worker import TaskManager

from reasonchip.net.protocol import DEFAULT_LISTENERS
from reasonchip.net.transports import worker_to_broker
from reasonchip.net.transports import SSLClientOptions


from .exit_code import ExitCode
from .command import AsyncCommand

log = logging.getLogger(__name__)


class WorkerCommand(AsyncCommand):

    def __init__(self):
        super().__init__()
        self._die = asyncio.Event()

    @classmethod
    def command(cls) -> str:
        """
        Returns the string command used to invoke this command.
        """
        return "worker"

    @classmethod
    def help(cls) -> str:
        """
        Returns a brief help description of the command.
        """
        return "Launch an engine process to perform work for a broker"

    @classmethod
    def description(cls) -> str:
        """
        Returns a detailed multi-line description of the command.
        """
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
        """
        Builds and configures the argument parser for the command.

        :param parser: The argparse.ArgumentParser instance to configure.
        """
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
        Main entry point for running the worker command.

        Sets up SSL context and transport to the broker, initializes engine and task manager, and runs the event loop.

        :param args: Parsed command line arguments.
        :param rem: Remaining arguments (not used).

        :return: ExitCode indicating success or failure.
        """

        if not args.collections:
            args.collections = ["."]

        ssl_options = SSLClientOptions.from_args(args)
        ssl_context = ssl_options.create_ssl_context() if ssl_options else None

        # Create the transport to communicate with the broker with SSL if needed
        transport = worker_to_broker(
            args.broker,
            ssl_client_options=ssl_options,
            ssl_context=ssl_context,
        )

        await self.setup_signal_handlers()

        try:
            log.info("Starting Engine with collections: %s", args.collections)

            # Let us create the engine and initialize with pipeline collections
            engine: Engine = Engine()
            engine.initialize(pipelines=args.collections)

            # Create and start the task manager to handle work
            tm = TaskManager(
                engine=engine,
                transport=transport,
                max_capacity=args.tasks,
            )
            await tm.start()
            log.info("Task manager started with max capacity: %d", args.tasks)

            # Wait for signals or task manager to stop
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

                    # If the task manager still running stop it
                    if task_manager in wl:
                        log.info("Received stop signal, stopping task manager")
                        await tm.stop()

                if task_manager in done:
                    wl.remove(task_manager)
                    task_manager = None

                    # If we have not received stop signal set it
                    if task_wait in wl:
                        log.info("Task manager stopped, setting stop event")
                        self._die.set()

            # Shutdown the engine cleanly
            engine.shutdown()
            log.info("Engine shutdown complete")
            return ExitCode.OK

        except rex.ReasonChipException as ex:
            msg = rex.print_reasonchip_exception(ex)
            log.error("ReasonChip exception occurred: %s", msg)
            print(msg)
            return ExitCode.ERROR

        except Exception as ex:
            log.error("Unhandled exception occurred: %s", ex, exc_info=True)
            print(f"************** UNHANDLED EXCEPTION **************")
            print(f"\n\n{ex}\n\n")
            traceback.print_exc()
            return ExitCode.ERROR

    async def _handle_signal(self, signame: str) -> None:
        """
        Handles incoming signals by setting the internal event to trigger shutdown.

        :param signame: The name of the signal received.
        """
        log.info("Received signal: %s", signame)
        self._die.set()

    async def setup_signal_handlers(self):
        """
        Setup signal handlers for SIGINT, SIGTERM and SIGHUP to handle graceful shutdown.
        """
        loop = asyncio.get_event_loop()
        for signame in {"SIGINT", "SIGTERM", "SIGHUP"}:
            loop.add_signal_handler(
                getattr(signal, signame),
                lambda signame=signame: asyncio.create_task(
                    self._handle_signal(signame)
                ),
            )
        log.info("Signal handlers established for SIGINT, SIGTERM, SIGHUP")
