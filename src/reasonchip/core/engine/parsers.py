# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import munch
import re
import ast

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


# ------------------------- SAFE BUILTINS -----------------------------------

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
    "iter": iter,
    "next": next,
    # Add any other safe built-in functions you want to allow.
    "escape": escape,
    "unescape": unescape,
}


# ------------------- EVALUATOR -----------------------------------------------


def evaluator(expr: str, variables: munch.Munch) -> typing.Any:

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
        raise rex.EvaluationException(expr) from e

    return result


# ------------------- EXECUTOR ------------------------------------------------


async def executor(code: str, variables: munch.Munch) -> typing.Any:

    tree = ast.parse(code)

    if len(tree.body) == 0:
        return None

    last_node = tree.body[-1]

    if isinstance(last_node, ast.Expr):
        return eval(
            code,
            {
                "__builtins__": {
                    **SAFE_BUILTINS,
                    **{
                        "__import__": __import__,
                        "print": print,
                    },
                },
            },
            variables,
        )

    exec(
        code,
        {
            "__builtins__": {
                **SAFE_BUILTINS,
                **{
                    "__import__": __import__,
                    "print": print,
                },
            },
        },
        variables,
    )

    if isinstance(last_node, ast.Assign):
        target = last_node.targets[0]
        if isinstance(target, ast.Name):
            return variables.get(target.id)

    return None
