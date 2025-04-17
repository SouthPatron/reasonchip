# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import logging

log = logging.getLogger(__name__)


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
        log.debug(f"ParsingException initialized with source: {source}")

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
        log.debug(
            f"TaskParseException initialized with task_no: {task_no}, message: {message}, errors: {errors}"
        )

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
        log.debug(
            f"PipelineFormatException initialized with message: {message}"
        )

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
        log.debug(
            f"RegistryException initialized with module_name: {module_name}, function_name: {function_name}"
        )

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
        log.debug(f"MalformedChipException initialized with reason: {reason}")

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
        log.debug(f"ValidationException initialized with source: {source}")

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
        log.debug(
            f"NoSuchPipelineDuringValidationException initialized with task_no: {task_no}, pipeline: {pipeline}"
        )

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
        log.debug(
            f"NoSuchChipDuringValidationException initialized with task_no: {task_no}, chip: {chip}"
        )

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
        log.debug(
            f"NestedValidationException initialized with task_no: {task_no}"
        )

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
        log.debug(
            f"NestedProcessorException initialized with pipeline_name: {pipeline_name}, task_no: {task_no}"
        )

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
        log.debug(
            f"NoSuchPipelineException initialized with pipeline: {pipeline}"
        )

    def __str__(self) -> str:
        resp = f"Pipeline not found: {self.pipeline}\n"
        return resp


class NoSuchChipException(ProcessorException):
    """Raised when a chip is not found."""

    def __init__(self, chip: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chip: str = chip
        log.debug(f"NoSuchChipException initialized with chip: {chip}")

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
        log.debug(
            f"InvalidChipParametersException initialized with chip: {chip}, errors: {errors}"
        )

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
        log.debug(f"ChipException initialized with chip: {chip}")

    def __str__(self) -> str:
        resp = f"Chip failed: {self.chip}"
        return resp


class VariableNotFoundException(ProcessorException):
    """Raised when a variable is not found."""

    def __init__(self, variable: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.variable: str = variable
        log.debug(
            f"VariableNotFoundException initialized with variable: {variable}"
        )

    def __str__(self) -> str:
        resp = f"Variable not found: {self.variable}"
        return resp


class EvaluationException(ProcessorException):
    """Raised when an evaluation fails."""

    def __init__(self, expr: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.expr = expr
        log.debug(f"EvaluationException initialized with expr: {expr}")

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
        log.debug(
            f"TerminateRequestException initialized with result: {result}"
        )


# -------------------------- PRETTY PRINTER ---------------------------------


def print_reasonchip_exception(ex: ReasonChipException) -> str:
    """
    Pretty print a ReasonChipException and its causes recursively.

    :param ex: The ReasonChipException instance to be printed.
    :return: A formatted string representing the exception chain.
    """

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
