import typing
import argparse
import re
import grpc
import json
import sys

from reasonchip.core.engine.context import Variables
from reasonchip.net.grpc import (
    reasonchip_pb2,
    reasonchip_pb2_grpc,
)

from .exit_code import ExitCode
from .command import AsyncCommand


class GrpcStreamCommand(AsyncCommand):

    @classmethod
    def command(cls) -> str:
        return "grpc-stream"


    @classmethod
    def help(cls) -> str:
        return "Stream several pipeline requests over gRPC"


    @classmethod
    def description(cls) -> str:
        return """
This command connects to a remote gRPC ReasonChip and streams several
pipelines. You may specify variables on the command line.
"""


    @classmethod
    def build_parser(cls, parser: argparse.ArgumentParser):
        parser.add_argument(
            "pipeline",
            metavar="<name>",
            help="Pipeline name",
        )
        parser.add_argument(
            "--set",
            action="append",
            default=[],
            metavar="key=value",
            type=str,
            help="Set or override a configuration key-value pair."
        )
        parser.add_argument(
            '--vars',
            action='append',
            default=[],
            metavar='<variable file>',
            type=str,
            help="Variable file to load into context"
        )


    async def main(
        self,
        args: argparse.Namespace,
        rem: typing.List[str],
    ) -> ExitCode:
        """
        Main entry point for the application.
        """
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


        # Create the channel
        channel = grpc.insecure_channel("localhost:50051")
        stub = reasonchip_pb2_grpc.ReasonChipServiceStub(channel)

        # Now perform the streaming
        self._stream_pipeline(
            stub,
            pipeline = args.pipeline,
            variables = variables,
        )

        return ExitCode.OK


    def _stream_pipeline(
        self,
        stub,
        pipeline: str,
        variables: Variables,
    ):
        def request_iterator():
            vdict = variables.vdict
            variables_json = json.dumps(vdict)

            yield reasonchip_pb2.PipelineRequest(
                pipeline = pipeline,
                variables = variables_json,
            )

            # Read the data from stdin, anything, and send it
            while True:
                data = sys.stdin.buffer.read()
                yield reasonchip_pb2.PipelineRequest(
                    pipeline = None,
                    variables = None,
                )


        response_iterator = stub.StreamPipeline(request_iterator())
        for response in response_iterator:
            print(f"Received response: {response}")


