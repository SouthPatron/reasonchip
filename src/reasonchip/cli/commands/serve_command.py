# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import argparse
import signal
import asyncio
import traceback
import re

from pathlib import Path

from reasonchip.core.engine.workflows import WorkflowLoader
from reasonchip.core.engine.engine import Engine, WorkflowSet
from reasonchip.net.amqp_consumer import AmqpConsumer, AMQPCallbackResp

from .exit_code import ExitCode
from .command import AsyncCommand


class ServeCommand(AsyncCommand):

    def __init__(self):
        super().__init__()
        self._die = asyncio.Event()

    @classmethod
    def command(cls) -> str:
        return "serve"

    @classmethod
    def help(cls) -> str:
        return "Serve requests on a queue"

    @classmethod
    def description(cls) -> str:
        return """
This is an engine process which serves requests received from a queue.

You may specify how many parallel tasks may be executed at any one time.

The AMQP url should be specified like these examples:

    amqp://localhost
    amqp://user:pass@localhost
    amqp://user:pass@localhost/vhost_name
    amqp://user:pass@rabbit.example.com:5672/vhost_name
    amqps://user:pass@rabbit.example.com:5671/vhost_name
    amqps://user:pass@rabbit.example.com:5671/vhost_name?heartbeat=30&connection_timeout=60
    amqp://user%40example.com:pa%3Ass@rabbit.example.com:5672/%2F

"""

    @classmethod
    def build_parser(cls, parser: argparse.ArgumentParser):
        parser.add_argument(
            "--collection",
            dest="collections",
            action="append",
            default=[],
            metavar="name=<directory>",
            type=str,
            help="List of named collections.",
        )
        parser.add_argument(
            "--amqp-url",
            metavar="<url>",
            type=str,
            default="amqp://localhost",
            help="AMQP URL",
        )
        parser.add_argument(
            "--amqp-queue",
            metavar="<name>",
            type=str,
            required=True,
            help="Queue name",
        )
        parser.add_argument(
            "--amqp-exchange",
            metavar="<name>",
            type=str,
            default="",
            help="Exchange name",
        )
        parser.add_argument(
            "--amqp-routing-key",
            metavar="<key>",
            type=str,
            default="",
            help="Routing key",
        )
        parser.add_argument(
            "--tasks",
            metavar="<number>",
            type=int,
            default=4,
            help="The number of tasks to run in parallel",
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
            print("No collections specified")
            return ExitCode.ERROR

        await self.setup_signal_handlers()

        workflow_loader = WorkflowLoader()
        workflow_set = WorkflowSet()

        try:
            # Create the WorkflowSet.
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

            # Create the Engine and EngineContext
            engine = Engine(workflow_set=workflow_set)

            # Now we create a consumer
            async def amqp_callback(packet: bytes) -> AMQPCallbackResp:
                print(f"Received packet: {packet}")
                return AMQPCallbackResp.ACK

            amqp = AmqpConsumer(callback=amqp_callback)
            rc = amqp.initialize(
                amqp_url=args.amqp_url,
                queue_name=args.amqp_queue,
                exchange_name=args.amqp_exchange,
                routing_key=args.amqp_routing_key,
            )
            if rc == False:
                raise ValueError(
                    f"Failed to initialize AMQP consumer with URL: {args.amqp_url}, "
                    f"queue: {args.amqp_queue}, exchange: {args.amqp_exchange}, "
                    f"routing key: {args.amqp_routing_key}"
                )

            await amqp.start()

            # Wait for signals or the client to stop
            task_wait = asyncio.create_task(self._die.wait())
            task_consumer = amqp.task()

            wl = [task_wait, task_consumer]

            while wl:
                done, _ = await asyncio.wait(
                    wl,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if task_wait in done:
                    wl.remove(task_wait)
                    task_wait = None

                    if task_consumer in wl:
                        await amqp.stop()

                if task_consumer in done:
                    wl.remove(task_consumer)
                    task_consumer = None

                    if task_wait in wl:
                        self._die.set()

            # Shutdown
            amqp.shutdown()

            # Exit
            return ExitCode.OK

        except Exception:
            print(f"************** UNHANDLED EXCEPTION **************")
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
