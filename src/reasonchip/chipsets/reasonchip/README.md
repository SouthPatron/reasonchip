# ReasonChip Chipsets

## Overview

This directory contains the core ReasonChip chipset components
providing asynchronous handling, logging, and standard byte streams
support. These modules enable async task waiting with timeouts,
structured logging, and reading/writing of stdin, stdout, and stderr
as bytes within ReasonChip pipelines.

## Filesystem Overview

| Location          | Description                                                    |
| ----------------- | --------------------------------------------------------------|
| [async.py](./async.py)   | Async task waiting with optional timeouts using asyncio tasks |
| [debug.py](./debug.py)   | Logging services supporting standard log levels              |
| [streams.py](./streams.py) | Stdin/stdout/stderr byte streams read/write operations        |

## Onboarding Approach

To onboard in ReasonChip chipset components:

1. Review `async.py` to understand asynchronous task waiting.
   It uses Pydantic models to encapsulate asyncio.Tasks and waits
   for completion or timeout, returning a status and response.

2. Examine `debug.py` for integrating standard logging levels.
   Gain familiarity with Python's logging library and how requests
   are modeled with Pydantic. This module synchronously logs messages
   at specified levels.

3. Study `streams.py` for byte-level I/O handling of stdin, stdout,
   and stderr. It covers reading fixed-size byte chunks or lines
   asynchronously, writing byte outputs, printing strings to stdout,
   and flushing buffers.

Developers should understand asyncio for async concurrency, Pydantic
for request/response modeling and validation, and the ReasonChip
Registry pattern for registering async handlers.

## Component Details

- **Async Handling**: Defines `WaitForRequest` for awaiting
  asyncio.Tasks with optional timeouts. Returns completion status
  and the awaited result or timeout indication.

- **Logging**: Provides log requests with level and message fields.
  Dispatches messages to Python's logging facility at the requested
  level.

- **Streams Handling**: Implements byte-based stdin reading (by max
  bytes or line), writing to stdout and stderr with buffer flushing,
  and printing string messages to stdout. Success flags signal
  operation outcome.

## Registry Pattern

All async handlers are registered with the ReasonChip `Registry`.
Request and response data structures use Pydantic BaseModels to
enforce type safety and validation, facilitating clear interface
contracts for pipeline integration.

---

This README documents the essential async, debug, and stream modules
that constitute the core ReasonChip chipset layer.
