# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing


# --------- Base Exception --------------------------------------------------


class ReasonChipException(Exception):
    """Base class for exceptions in this module."""

    pass


# --------- General Exceptions ----------------------------------------------


class ConfigurationException(ReasonChipException):
    pass


# --------- Workflow Exceptions ---------------------------------------------


class WorkflowException(ReasonChipException):
    """Raised when a Workflow exception occurs."""

    pass


class WorkflowLoadException(WorkflowException):
    """Raised when a Workflow can't be loaded."""

    pass


class WorkflowAlreadyExistsException(WorkflowException):
    """Raised when a Workflow already exists and cannot be overwritten."""

    pass


class WorkflowNotFoundException(WorkflowException):
    """Raised when a Workflow cannot be found."""

    pass


class WorkflowStepMalformedException(WorkflowException):
    """Raised when a Workflow step is malformed."""

    pass


# --------- Engine Exceptions ------------------------------------------------


class EngineException(ReasonChipException):
    """Base class for exceptions in the Engine module."""

    pass


class TerminateEngineException(EngineException):
    """Raised when the Engine needs to be terminated."""

    def __init__(
        self,
        rc: typing.Any,
    ):
        self.rc = rc


class RestartEngineException(EngineException):
    """Raised when the Engine needs to be restarted."""

    def __init__(
        self,
        name: str,
        *args,
        **kwargs,
    ):
        self.name = name
        self.args = args
        self.kwargs = kwargs
