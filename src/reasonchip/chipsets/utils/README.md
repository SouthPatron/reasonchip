# Utilities Chipsets

## Overview

This directory contains utility chipsets for the ReasonChip engine. Each chipset
provides asynchronous commands that perform common tasks such as string
processing, JSON serialization/deserialization, and time-related operations.

The chipsets follow a request-response pattern using Pydantic models and are
registered centrally for invocation by the ReasonChip engine.

## Filesystem Overview

| Location              | Description                                   |
|-----------------------|-----------------------------------------------|
| [strings.py](./strings.py)   | Chipset for string utilities such as removing code blocks |
| [json.py](./json.py)         | Chipset providing JSON encoding and decoding commands       |
| [time.py](./time.py)         | Chipset exposing time utilities such as asynchronous sleep  |

## Onboarding Approach

To onboard onto these chipsets, start by understanding the core design pattern:

- Each chipset defines one or more commands as async functions decorated with
  `@Registry.register`.
- Commands accept a Pydantic model as input and return a Pydantic model as output,
  capturing request parameters and response structure respectively.
- Error handling is done by returning responses with a status field indicating
  "OK" or "ERROR" and including error messages where appropriate.
- The commands are asynchronous but often perform synchronous operations, registered
  to be called within the ReasonChip engine asynchronously.

Knowledge required:

- Familiarity with asyncio in Python and async/await syntax.
- Understanding of Pydantic for data validation and model definitions.
- Basic knowledge of how registration decorators create a command registry.
- JSON serialization and deserialization concepts.
- Regular expressions for pattern matching in strings.

Begin by reviewing the `strings.py` chipset to see a practical example involving
regexp and text processing. Then study `json.py` for typical JSON command
patterns. Finally, look at `time.py` for a simple synchronous sleep wrapped as
an asynchronous command.

## Design Concepts

- **Command Pattern**: Each utility function is exposed as a command with clearly
defined requests and responses for strong typing and error reporting.

- **Registry Pattern**: The central `Registry.register` decorator collects commands
for invocation by ReasonChip.

- **Asynchronous Interface**: Even synchronous utilities are wrapped in async
functions to maintain a consistent async interface.

- **Pydantic Models**: Strictly typed data models provide validation and self-
documenting request/response schemas.

- **Error Handling**: Commands return structured responses with status and detailed
error messages for robust interfacing.

This organization enables clean, maintainable, and extensible utility chipsets that
can be integrated into the ReasonChip engine seamlessly.
