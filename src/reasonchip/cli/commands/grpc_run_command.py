import typing
import uuid
import argparse
import re
import json

from reasonchip.core.engine.context import Variables
from reasonchip.net import Api, Client, Multiplexor
from reasonchip.net.grpc import GrpcConnectionImpl

from .exit_code import ExitCode
from .command import AsyncCommand


class GrpcRunCommand(AsyncCommand):

    @classmethod
    def command(cls) -> str:
        return "grpc-run"


    @classmethod
    def help(cls) -> str:
        return "Run a remote pipeline over gRPC"


    @classmethod
    def description(cls) -> str:
        return """
This command connects to a remote gRPC server and runs a pipeline.

You may specify variables on the command line.
These variables will take precedence over variables already loaded within
the pipeline server.

The result of the pipeline, if any, is printed as a JSON response on a
single line. Remember that the pipeline defines the output format, so
the result may be any JSON object depending on which pipeline is run and
what it is supposed to return.
"""


    @classmethod
    def build_parser(cls, parser: argparse.ArgumentParser):
        parser.add_argument(
            "pipeline",
            metavar="<name>",
            help="Pipeline name",
        )
        parser.add_argument(
            "--cookie",
            action="store",
            default=None,
            metavar="<uuid>",
            type=str,
            help="Cookie to use for this request",
        )
        parser.add_argument(
            "--set",
            action="append",
            default=[],
            metavar="key=value",
            type=str,
            help="Set or override a configuration key-value pair"
        )
        parser.add_argument(
            '--vars',
            action='append',
            default=[],
            metavar='<variable file>',
            type=str,
            help="Variable file to load into context"
        )
        parser.add_argument(
            '--server',
            action='store',
            default='localhost:50051',
            metavar='<host[:port]>',
            type=str,
            help="gRPC server address"
        )


    async def main(
        self,
        args: argparse.Namespace,
        rem: typing.List[str],
    ) -> ExitCode:
        """
        Main entry point for the application.
        """

        # Generate a cookie for tracing
        ck = uuid.UUID(args.cookie) if args.cookie else uuid.uuid4()

        # Load variables
        variables = Variables()

        for x in args.vars:
            variables.load_file(x)

        for x in args.set:
            m = re.match(r"^(.*?)=(.*)$", x)
            if not m:
                raise ValueError(f"Invalid key value pair: {x}")

            key, value = m[1], m[2]
            variables.set(key, value)


        # Create the connection
        conn = GrpcConnectionImpl()
        rc = await conn.connect(
            target = args.server,
            max_message_length = 1 * (1024 * 1024),
        )
        if rc is False:
            raise ConnectionError(f"Failed to connect to {args.server}")

        # Create the multiplexor
        multiplexor = Multiplexor(impl = conn)
        await multiplexor.start()

        # Get a client
        api = Api(multiplexor = multiplexor)
        result = await api.run_pipeline(
            pipeline = args.pipeline,
            variables = variables.vdict,
            cookie = ck,
        )

        resp = { "cookie": ck, "result": result }
        resp_str = json.dumps(resp)
        print(resp_str)

        # Stop the multiplexor
        await multiplexor.stop()
        multiplexor = None

        # Disconnect the connection
        await conn.disconnect()
        conn = None

        return ExitCode.OK


