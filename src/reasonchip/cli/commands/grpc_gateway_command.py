import typing
import argparse
import re
import asyncio
import signal
import grpc

from concurrent import futures

from reasonchip.core import exceptions as rex
from reasonchip.net.gateways.grpc import (
    reasonchip_pb2_grpc,
    ReasonChipService,
)

from .exit_code import ExitCode
from .command import AsyncCommand


class GrpcGatewayCommand(AsyncCommand):

    def __init__(self):
        super().__init__()
        self._die: asyncio.Event = asyncio.Event()


    @classmethod
    def command(cls) -> str:
        return "grpc-gateway"


    @classmethod
    def help(cls) -> str:
        return "gRPC gateway"


    @classmethod
    def description(cls) -> str:
        return """Run a gRPC gateway to a broker."""


    @classmethod
    def build_parser(cls, parser: argparse.ArgumentParser):
        parser.add_argument(
            '--broker',
            metavar='<address>',
            required=True,
            help="Address to the broker"
        )
        parser.add_argument(
            '--listen',
            action='append',
            metavar='<host:port>',
            default = [],
            help="Host and optional port on which to listen",
        )


    async def main(
        self,
        args: argparse.Namespace,
        rem: typing.List[str],
    ) -> ExitCode:
        """
        Main entry point for the application.
        """
        await self.setup_signal_handlers()

        try:
            # Create the API server
            rchip = ReasonChipService(
                conn_helper = conn_helper,
            )

            # Build the gRPC server
            server = grpc.aio.server(futures.ThreadPoolExecutor(
                max_workers=10,
            ))
            reasonchip_pb2_grpc.add_ReasonChipServiceServicer_to_server(
                rchip,
                server
            )

            # Decide on the listen addresses
            if not args.listen:
                args.listen.append("[::]:50051")

            for x in args.listen:
                server.add_insecure_port(x)

            # Start the servers
            await server.start()

            for x in args.listen:
                print(f"gRPC Server started on: {x}")

            # Wait for signals or the server to stop
            task_wait = asyncio.create_task(self._wait_for_exit())

            await asyncio.wait(
                [task_wait],
                return_when = asyncio.FIRST_COMPLETED,
            )

            print(f" - Stopping the gRPC server...")
            await server.stop(120)

            print(f" - Stopping the socket server...")
            await socket_server.stop()
            print(f" - Server stopped")

            return ExitCode.OK

        except rex.ReasonChipException as ex:
            msg = rex.print_reasonchip_exception(ex)
            print(msg)
            return ExitCode.ERROR

        except Exception as ex:
            print(f"************** UNHANDLED EXCEPTION **************")
            print(f"\n\n{type(ex)}\n\n")
            print(ex)
            return ExitCode.ERROR


    async def _wait_for_exit(self) -> None:
        await self._die.wait()


    async def _handle_signal(self, signame: str) -> None:
        self._die.set()


    async def setup_signal_handlers(self):
        loop = asyncio.get_event_loop()
        for signame in {'SIGINT', 'SIGTERM', 'SIGHUP'}:
            loop.add_signal_handler(
                getattr(signal, signame),
                lambda: asyncio.create_task(self._handle_signal(signame))
            )

