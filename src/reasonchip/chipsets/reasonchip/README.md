# ReasonChip Chipsets

## Overview

This directory contains the ReasonChip core async, logging, and stream
handling components. These modules provide asynchronous task handling,
logging functionalities, and standard input/output byte stream access
for ReasonChip pipelines.

## Filesystem Overview

| Location          | Description                                  |
| ----------------- | --------------------------------------------|
| [async.py](./async.py)           | Asynchronous task handling (wait for completion with optional timeout) |
| [debug.py](./debug.py)           | Logging with multiple standard levels inside ReasonChip pipelines |
| [streams.py](./streams.py)       | Standard input, output, and error streams handling in bytes |

## Onboarding Approach

To understand the ReasonChip chipset components:

1. Start with `async.py` to understand the async task waiting mechanism.
   It introduces async/await patterns with timeout support using
   `asyncio.wait_for`.

2. Study `debug.py` which integrates logging at various levels into
   ReasonChip services. Familiarity with Python's logging module
   and Pydantic request/response modeling is essential.

3. Review `streams.py` to grasp how ReasonChip wraps stdin/stdout/stderr
   byte I/O within asynchronous request-response ReasonChip operations.
   This file handles reading and writing, flushing buffers, and
   provides both line-based and byte-based stdin reading.

Developers should be proficient in async programming with asyncio,
Pydantic for data validation/serialization, and the overall ReasonChip
registry system that registers async handlers for service calls.

## Component Details

- **Async Handling**: Uses `asyncio.Task` instances wrapped in Pydantic models
  to wait asynchronously with optional timeouts. Responses indicate
  success or timeout.

- **Logging**: Receives log requests with a level and message,
  then dispatches them synchronously via Python's logging module.
  Supports levels info, debug, warning, error, and critical.

- **Streams Handling**: Implements stdin read (fixed max bytes or lines),
  and stdout/stderr write of bytes, including flushing.
  Includes convenience print to stdout with success indication.

## Registry Mechanism

All main functions are registered via `Registry.register`, making them
available as callable ReasonChip services. Request and response schemas
are defined using Pydantic BaseModel for validation and typing.

---

This README outlines the core async, debug, and stream components
fundamental for ReasonChip chipset operations.
