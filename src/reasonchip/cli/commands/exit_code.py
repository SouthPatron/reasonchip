# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import enum
import logging

log = logging.getLogger(__name__)


class ExitCode(enum.IntEnum):
    """
    Enumeration of exit codes used by the application.

    Each member represents a specific type of termination status.
    """

    OK = 0
    COMMAND_LINE_ERROR = 1
    CONFIGURATION_PROBLEM = 2
    UNKNOWN_COMMAND = 3
    MODULE_NOT_FOUND = 4
    ERROR = 5
