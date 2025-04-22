# Exceptions

## Overview

This directory contains the exception class hierarchy used in the ReasonChip
project. These exceptions cover client-side errors, server-side errors,
parsing issues, validation failures, processor runtime problems, and flow
control exceptions arising during pipeline processing and execution.

## Filesystem Overview

| Location          | Description                           |
|-------------------|-------------------------------------|
| [exceptions.py](./exceptions.py) | Defines ReasonChip exception classes and hierarchies |

## Onboarding Approach

Start by understanding the `ReasonChipException` base class, from which all
custom exceptions inherit. Exceptions are grouped by the context of their
use:

- Client-side and server-side exceptions for boundary layer error handling.
- Parsing exceptions related to pipeline and task YAML or similar format parsing.
- Registry exceptions related to registration and malformed elements.
- Validation exceptions for pre-run pipeline validation.
- Processor exceptions raised during pipeline execution including chips,
  variable references, and evaluation errors.
- Flow exceptions used for control flow like termination.

Examine subclasses of `ParsingException` and `ValidationException` to see
how additional context such as task number and error details are captured.
Similarly, processor exceptions often hold the relevant pipeline, chip, or
variable name involved in the error.

Developers should be familiar with exception handling in Python, class
inheritance, and the structure of the ReasonChip pipeline and chip concepts to
best understand when each exception type is raised.

## Exception Class Structure

- The base `ReasonChipException` is extended by specific categories:
  - `ClientSideException`, `ServerSideException` for client/server event
  - `ParsingException` and subclasses for format and task parsing errors
  - `RegistryException`, for errors in chip registration
  - `ValidationException` subclasses for issues found before execution
  - `ProcessorException` and subclasses for runtime execution errors
  - `FlowException` and subclasses for flow control signals

- Each exception optionally carries metadata relevant to its category, such as
  task number, pipeline, chip name, error messages, or the source location.

- String representations (`__str__`) provide rich error messages for logging
  and user feedback.

## Exception Handling and Reporting

The module provides a utility function `print_reasonchip_exception` for
formatted output of exception chains, ensuring all wrapped causes are also
ReasonChip exceptions, allowing consistent reporting.

This structure centralizes error handling and clear exception propagation
throughout ReasonChip's pipeline processing.

## Notes

- Developers extending ReasonChip should inherit from these base exceptions or
  related subclasses to maintain consistency.
- Exception classes maintain concise interfaces focused on relevant metadata
  for error context.
- The hierarchy supports layered error handling from parsing to runtime phases.
