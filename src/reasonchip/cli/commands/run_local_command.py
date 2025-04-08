import typing
import argparse
import uuid
import re
import json

from reasonchip.core import exceptions as rex

from reasonchip.core.engine.engine import Engine
from reasonchip.core.engine.context import Variables

from .exit_code import ExitCode
from .command import AsyncCommand


class RunLocalCommand(AsyncCommand):


    @classmethod
    def command(cls) -> str:
        return "run-local"


    @classmethod
    def help(cls) -> str:
        return "Run a pipeline locally"


    @classmethod
    def description(cls) -> str:
        return "Run a pipeline locally"


    @classmethod
    def build_parser(cls, parser: argparse.ArgumentParser):
        parser.add_argument(
            '--collection',
            dest='collections',
            action='append',
            default=[],
            metavar='<collection root>',
            type=str,
            help="Root of a pipeline collection"
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
        parser.add_argument(
            '-e', '--entry',
            action='store',
            metavar='<entry>',
            type=str,
            required=True,
            help="Entry pipeline at which to start"
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
            args.collections = ["."]

        try:
            engine: Engine = Engine()
            engine.initialize(pipelines = args.collections)

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

            # Assign a job id
            variables.set("job_id", uuid.uuid4())

            # Run the engine
            rc = await engine.run(args.entry, variables)

            if rc:
                print(json.dumps(rc))

            # Shutdown the engine
            engine.shutdown()

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



