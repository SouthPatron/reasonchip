# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing

from .command import Command, AsyncCommand
from .exit_code import ExitCode

# Commands
from .broker_command import BrokerCommand
from .run_command import RunCommand
from .run_local_command import RunLocalCommand
from .worker_command import WorkerCommand


def get_commands() -> (
    typing.Dict[str, typing.Union[type[Command], type[AsyncCommand]]]
):
    return {
        x.command(): x
        for x in [
            # Socket commands
            BrokerCommand,
            RunCommand,
            RunLocalCommand,
            WorkerCommand,
        ]
    }


__all__ = [
    "ExitCode",
    "Command",
    "AsyncCommand",
    "get_commands",
]
