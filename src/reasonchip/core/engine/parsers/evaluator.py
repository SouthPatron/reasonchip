# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import munch

from ... import exceptions as rex

# ------------------------ LEXER -------------------------------------------


def evaluator(expr: str, variables: munch.Munch):

    SAFE_BUILTINS = {
        "abs": abs,
        "min": min,
        "max": max,
        "sum": sum,
        "round": round,
        "pow": pow,
        "len": len,
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        "list": list,
        "tuple": tuple,
        "dict": dict,
        "sorted": sorted,
        "enumerate": enumerate,
        "range": range,
        "all": all,
        "any": any,
        "repr": repr,
        "format": format,
        "type": type,
        "isinstance": isinstance,
    }

    try:
        # Evaluate the expression in a restricted environment.
        result = eval(
            expr,
            {
                "__builtins__": SAFE_BUILTINS,
            },
            variables,
        )
    except Exception as e:
        raise rex.EvaluationException(expr=expr) from e

    return result
