# Engine Parsers

## Overview

This directory contains parser components responsible for interpreting
and evaluating expressions within the ReasonChip engine. It includes
utilities to parse conditions and evaluate expressions in a controlled
environment.

## Filesystem Overview

| Location                      | Description                               |
|-------------------------------|-------------------------------------------|
| [conditional.py](./conditional.py) | Expression evaluation and conditional parsing |

## Expression Evaluation

The `conditional.py` module provides a function `evaluate` which
safely evaluates Python expressions based on a given variable
context. It runs the expression in a restricted environment with
no built-in functions to prevent unsafe operations.

Errors during evaluation raise a custom `EvaluationException` to
signal failure in conditional parsing.

## Logging

The evaluation process includes debug logging of the expression and
its result, and error logging if evaluation fails.

## Exceptions

The module depends on `exceptions` from the engine to handle
evaluation errors uniformly.
