from ... import exceptions as rex

from ..context import Variables

# ------------------------ LEXER -------------------------------------------


def evaluate(expr: str, variables: Variables):

    try:
        # Evaluate the expression in a restricted environment.
        result = eval(expr, {"__builtins__": {}}, variables.vobj)
    except Exception as e:
        raise rex.EvaluationException(expr = expr) from e

    return result

