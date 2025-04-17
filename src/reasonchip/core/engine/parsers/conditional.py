# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import logging

from ... import exceptions as rex
from ..context import Variables

log = logging.getLogger(__name__)

# ------------------------ LEXER -------------------------------------------


def evaluate(expr: str, variables: Variables):
    """
    Evaluate the given expression as a Python expression using the provided variables.

    The evaluation is performed in a restricted environment to avoid unsafe builtins.

    :param expr: The expression string to evaluate.
    :param variables: Variables object providing the context variables for evaluation.

    :return: The result of the evaluated expression.
    """
    try:
        # Evaluate the expression in a restricted environment.
        result = eval(expr, {"__builtins__": {}}, variables.vobj)
        log.debug("Evaluated expression '%s' to result: %s", expr, result)
    except Exception as e:
        log.error("Error evaluating expression '%s': %s", expr, e)
        raise rex.EvaluationException(expr=expr) from e

    return result
