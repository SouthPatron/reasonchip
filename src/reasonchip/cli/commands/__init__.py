import typing

from .command import Command, AsyncCommand
from .exit_code import ExitCode

# Socket commands
from .broker_command import BrokerCommand
from .run_command import RunCommand
from .run_local_command import RunLocalCommand
from .worker_command import WorkerCommand

# gRPC commands
#from .grpc_gateway_command import GrpcGatewayCommand
#from .grpc_run_command import GrpcRunCommand
#from .grpc_stream_command import GrpcStreamCommand


def get_commands() -> typing.Dict[str, typing.Union[type[Command], type[AsyncCommand]]]:
    return {
        x.command() : x
        for x in [

            # Socket commands
            BrokerCommand,
            RunCommand,
            RunLocalCommand,
            WorkerCommand,

            # gRPC commands
            #grpc_gateway_command,
        ]
    }


__all__ = [
    'ExitCode',
    'Command',
    'AsyncCommand',
    'get_commands',
]

