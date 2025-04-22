# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import munch
import re

from reasonchip.core import exceptions as rex

# ------------------------ LEXER -------------------------------------------


def escape(text: str) -> str:
    """
    Escapes all {{ ... }} expressions that are not already escaped with a backslash.
    It replaces them with \\{{ ... }} to prevent Jinja interpolation.
    """
    # This regex matches {{ ... }} not preceded by a backslash
    pattern = r"(?<!\\){{(.*?)}}"

    # Replace with escaped version
    return re.sub(pattern, r"\\{{\1}}", text)


def unescape(text: str) -> str:
    """
    Unescapes all expressions that were escaped with a backslash,
    i.e., converts \\{{ ... }} back to {{ ... }}.
    """
    pattern = r"\\{{(.*?)}}"
    return re.sub(pattern, r"{{\1}}", text)


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
        "reversed": reversed,
        "enumerate": enumerate,
        "range": range,
        "all": all,
        "any": any,
        "repr": repr,
        "format": format,
        "type": type,
        "isinstance": isinstance,
        # Add any other safe built-in functions you want to allow.
        "escape": escape,
        "unescape": unescape,
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
