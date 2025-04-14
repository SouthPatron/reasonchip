# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

from ... import exceptions as rex

from ..context import Variables

# ------------------------ LEXER -------------------------------------------


def evaluate(expr: str, variables: Variables):

    try:
        # Evaluate the expression in a restricted environment.
        result = eval(expr, {"__builtins__": {}}, variables.vobj)
    except Exception as e:
        raise rex.EvaluationException(expr=expr) from e

    return result
