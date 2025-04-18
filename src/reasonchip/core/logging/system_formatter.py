# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import datetime
import logging
import logging.config
import traceback
import json


class SystemFormatter(logging.Formatter):

    stack_depth: typing.Optional[int] = None

    def format(self, record: logging.LogRecord) -> str:
        if self._fmt is None:
            return ""

        rc = super().format(record)

        if record.exc_info and record.exc_info[0]:
            exclass = record.exc_info[0].__name__
            exc = record.exc_info[1]

            rc = f"{rc} : [EXCEPTION]"
            rc = f"{rc} : [{record.filename}({record.lineno})]"
            rc = f"{rc} : [{exclass}] [{exc}]"

            stack_trace_lines = traceback.format_exception(*record.exc_info)
            stack_trace_one_line = "".join(stack_trace_lines).replace(
                "\n", "\\n"
            )
            stack_trace_json = json.dumps(stack_trace_one_line)
            rc = f"{rc} : [TRACE] {stack_trace_json}"

        return rc

    def formatTime(self, record, datefmt=None):
        ct = datetime.datetime.utcfromtimestamp(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime("%Y%m%dT%H%M%SZ")
            s = "%s.%03d" % (t, record.msecs)
        return s

    def formatException(self, ei) -> str:
        return ""
