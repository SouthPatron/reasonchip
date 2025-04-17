# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import datetime
import logging
import traceback
import json

log = logging.getLogger(__name__)


class SystemFormatter(logging.Formatter):
    """
    Custom log formatter to format log records with optional detailed exception information.

    Attributes:
        stack_depth (typing.Optional[int]): Optional depth control for stack trace formatting (not used in current implementation).
    """

    stack_depth: typing.Optional[int] = None

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record into a string. If an exception is present, format exception details including a compact stack trace.

        :param record: The log record to format.
        :return: A formatted log string.
        """
        if self._fmt is None:
            log.debug("Format string is None, returning empty string.")
            return ""

        # Format the basic log record using parent class
        rc = super().format(record)
        log.debug(f"Basic formatted record: {rc}")

        # If there is exception info, append detailed exception information and stack trace
        if record.exc_info and record.exc_info[0]:
            exclass = record.exc_info[0].__name__
            exc = record.exc_info[1]

            # Append exception class and message
            rc = f"{rc} : [EXCEPTION]"
            rc = f"{rc} : [{record.filename}({record.lineno})]"
            rc = f"{rc} : [{exclass}] [{exc}]"
            log.debug(f"Exception info appended: class={exclass}, exc={exc}")

            # Format exception stack trace into one-line JSON string
            stack_trace_lines = traceback.format_exception(*record.exc_info)

            # Combine and escape newlines for a single line
            stack_trace_one_line = "".join(stack_trace_lines).replace(
                "\n", "\\n"
            )
            stack_trace_json = json.dumps(stack_trace_one_line)
            rc = f"{rc} : [TRACE] {stack_trace_json}"
            log.debug("Stack trace appended to log message.")

        return rc

    def formatTime(self, record, datefmt=None):
        """
        Format the creation time of the log record.

        :param record: The log record.
        :param datefmt: Optional date format string.
        :return: Formatted time string.
        """
        ct = datetime.datetime.utcfromtimestamp(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime("%Y%m%dT%H%M%SZ")

            # Format timestamp with milliseconds
            s = "%s.%03d" % (t, record.msecs)
        log.debug(f"Formatted time: {s}")
        return s

    def formatException(self, ei) -> str:
        """
        Override to control exception formatting; returns empty string as custom formatting is handled in format().

        :param ei: Exception info tuple.
        :return: Empty string.
        """
        log.debug(
            "formatException called but overridden to return empty string."
        )
        return ""
