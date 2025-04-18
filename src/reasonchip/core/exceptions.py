# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing


class ReasonChipException(Exception):
    """Base class for exceptions in this module."""

    pass


# --------- Client-side Exceptions ------------------------------------------


class ClientSideException(ReasonChipException):
    pass


# --------- Server-side Exceptions ------------------------------------------


class ServerSideException(ReasonChipException):
    pass


# --------- General Exceptions ----------------------------------------------


class ConfigurationException(ReasonChipException):
    pass


class TooBusyException(ReasonChipException):
    pass


# --------- Parsing Exceptions ----------------------------------------------


class ParsingException(ReasonChipException):
    """Raised when a parsing error occurs."""

    def __init__(self, source: typing.Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source = source

    def __str__(self):
        resp = f"""PARSING EXCEPTION

There was a problem parsing a pipeline or task.
The location of the error is:

LOCATION: {self.source}
"""
        return resp


class TaskParseException(ParsingException):
    """Raised when a task cannot be parsed."""

    def __init__(
        self,
        message: str,
        task_no: int,
        errors: typing.Optional[typing.List] = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.message = message
        self.task_no = task_no
        self.errors = errors

    def __str__(self):
        resp = f"""Task#: {self.task_no + 1}
Message: {self.message}
"""
        if self.errors:
            for m in self.errors:
                loc = m.get("loc", None)
                msg = m.get("msg", None)

                resp += f"\nLocation: {loc}"
                resp += f"\nReason: {msg}\n"

        return resp


class PipelineFormatException(ParsingException):
    """The PipelineFile contains an error."""

    def __init__(self, message: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = message

    def __str__(self):
        resp = f"Message: {self.message}.\n"
        return resp


# --------- Registry Exceptions ----------------------------------------------


class RegistryException(ReasonChipException):
    """The Registry experienced an error."""

    def __init__(
        self,
        module_name: typing.Optional[str] = None,
        function_name: typing.Optional[str] = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.module_name = module_name
        self.function_name = function_name

    def __str__(self):
        resp = "REGISTRY EXCEPTION\n"
        if self.module_name is not None:
            resp += f"\nModule: {self.module_name}"

        if self.function_name is not None:
            resp += f"\nFunction: {self.function_name}"

        return resp


class MalformedChipException(RegistryException):
    """Raised when a chip is malformed."""

    def __init__(
        self,
        reason: typing.Optional[str] = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.reason = reason

    def __str__(self):
        resp = "The chip is malformed.\n"
        resp += f"\n{self.reason}\n"
        return resp


# --------- Validation Exceptions --------------------------------------------


class ValidationException(ReasonChipException):
    """An exception raised during validation of the pipelines."""

    def __init__(self, source: typing.Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source = source

    def __str__(self) -> str:
        resp = f"""VALIDATION EXCEPTION

There was a problem validating the pipelines and tasks prior to execution.

The source was: {self.source}
"""
        return resp


class NoSuchPipelineDuringValidationException(ValidationException):
    """Raised when a pipeline is not found during validation."""

    def __init__(self, task_no: int, pipeline: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_no = task_no
        self.pipeline = pipeline

    def __str__(self) -> str:
        resp = f"""In task #{self.task_no + 1}, the specified pipeline does not exist.

Pipeline: {self.pipeline}
"""
        return resp


class NoSuchChipDuringValidationException(ValidationException):
    """Raised when a chip is not found during validation."""

    def __init__(self, task_no: int, chip: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_no = task_no
        self.chip = chip

    def __str__(self) -> str:
        resp = f"""In task #{self.task_no + 1}, the specified chip does not exist.

Chip: {self.chip}
"""
        return resp


class NestedValidationException(ValidationException):
    """Raised when a validation exception is nested."""

    def __init__(self, task_no: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_no = task_no

    def __str__(self) -> str:
        resp = f"Nested path task#: {self.task_no + 1}"
        return resp


# --------- Processor Exceptions ---------------------------------------------


class ProcessorException(ReasonChipException):
    """An exception raised from the processor."""

    def __str__(self) -> str:
        resp = "PROCESSOR EXCEPTION\n"
        return resp


class NestedProcessorException(ProcessorException):
    """A nested path processor exception."""

    def __init__(
        self,
        pipeline_name: typing.Optional[str] = None,
        task_no: typing.Optional[int] = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.pipeline_name = pipeline_name
        self.task_no = task_no

    def __str__(self) -> str:
        resp = ""

        if self.pipeline_name:
            resp += f"Pipeline: {self.pipeline_name} "

        if self.task_no:
            resp += "Task#: {self.task_no + 1}"

        return resp


class NoSuchPipelineException(ProcessorException):
    """Raised when a pipeline is not found."""

    def __init__(self, pipeline: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pipeline: str = pipeline

    def __str__(self) -> str:
        resp = f"Pipeline not found: {self.pipeline}\n"
        return resp


class NoSuchChipException(ProcessorException):
    """Raised when a chip is not found."""

    def __init__(self, chip: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chip: str = chip

    def __str__(self) -> str:
        resp = f"Chip not found: {self.chip}"
        return resp


class InvalidChipParametersException(ProcessorException):
    """Raised when the parameters for a chip call don't validate."""

    def __init__(
        self,
        chip: str,
        errors: typing.Optional[typing.List] = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.chip = chip
        self.errors = errors

    def __str__(self):
        resp = f"""Chip: {self.chip}"""
        if self.errors:
            for m in self.errors:
                loc = m.get("loc", None)
                msg = m.get("msg", None)

                resp += f"\nLocation: {loc}"
                resp += f"\nReason: {msg}\n"

        return resp


class ChipException(ProcessorException):
    """Raised when a chip call fails."""

    def __init__(self, chip: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chip: str = chip

    def __str__(self) -> str:
        resp = f"Chip failed: {self.chip}"
        return resp


class VariableNotFoundException(ProcessorException):
    """Raised when a variable is not found."""

    def __init__(self, variable: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.variable: str = variable

    def __str__(self) -> str:
        resp = f"Variable not found: {self.variable}"
        return resp


class EvaluationException(ProcessorException):
    """Raised when an evaluation fails."""

    def __init__(self, expr: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.expr = expr

    def __str__(self) -> str:
        resp = f"Expression failed: {self.expr}"
        return resp


class LoopVariableNotIterable(ProcessorException):
    """Raised when a loop variable is not iterable."""

    pass


# --------- Flow Exceptions --------------------------------------------------


class FlowException(ProcessorException):
    """A flow exception raised from the chip."""

    pass


class TerminateRequestException(FlowException):
    """Raised when everything should terminate."""

    def __init__(self, result: typing.Any):
        self.result = result


# -------------------------- PRETTY PRINTER ---------------------------------


def print_reasonchip_exception(ex: ReasonChipException) -> str:

    resp = f"************** ReasonChip Exception *************\n"

    if len(ex.args) > 0:
        resp += f"\n{ex.args[0]}\n"

    tmp = ex

    while tmp is not None:
        if isinstance(tmp, ReasonChipException):
            resp += f"\n{tmp}\n"
        else:
            raise RuntimeError(
                "\n*********************************************************\n"
                "All ReasonChip exception causes must be ReasonChip exceptions too.\n"
                "Anything else indicates an unhandled exception.\n"
                "*********************************************************\n"
            ) from tmp

        if tmp.__cause__:
            tmp = tmp.__cause__
        else:
            tmp = None

    return resp
