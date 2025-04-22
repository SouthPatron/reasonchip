# HTTP Transport Common

## Overview

This directory contains foundational HTTP transport components for ReasonChip.
It provides shared abstractions such as client session management and
callback hooks that are used across HTTP transport implementations.

## Filesystem Overview

| Location                | Description                                   |
| ----------------------- | --------------------------------------------- |
| [common.py](./common.py) | ClientSession dataclass and CallbackHooks interface |
| [fastapi/](./fastapi/)  | FastAPI-based HTTP transport implementation   |

## Onboarding Approach

Start by understanding the `ClientSession` dataclass in `common.py`, which
encapsulates a client connection session including its unique identifier,
termination signal, and outgoing packet queue. Then review the `CallbackHooks`
dataclass which holds asynchronous callbacks for connection lifecycle events:
new connection, packet read, and disconnection.

These components abstract the transport session management and event handling
so that HTTP server implementations like FastAPI can plug into the common
framework. Familiarity with Python async programming, `asyncio` constructs
(`Event`, `Queue`), and dataclasses is required.

Additionally, knowledge of the ReasonChip `SocketPacket` protocol and packet
handling is essential to understand how data flows through the session.

Next, explore the `fastapi` subdirectory to see how these abstractions
are implemented concretely with an async HTTP framework, tying together
callback handling with web request lifecycle.

## Architecture and Design

The design splits concerns between generic session and callback management
(`common.py`), and specific HTTP transport implementations (`fastapi`).

- `ClientSession` manages state and in-flight packets per client connection.

- `CallbackHooks` decouples transport-level events from application-level logic.

- HTTP transport modules create and manage `ClientSession` objects,
  invoke callbacks on events, and handle request/response flows.

This modular design enables adding new HTTP transports without rewriting
session and callback code.

## Integration Notes

The `common.py` module imports ReasonChip's `SocketPacket` and `PacketType`
protocol types, linking transport layer to protocol layer. Implementations
using `ClientSession` should handle packets asynchronously for concurrency.

The callbacks use `async` functions for non-blocking event processing.

---

This directory forms the backbone for HTTP-based network transport layers
within ReasonChip, providing consistent session handling and lifecycle
hooks to be leveraged by HTTP server implementations.
