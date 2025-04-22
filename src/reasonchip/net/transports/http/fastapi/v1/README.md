# FastAPI HTTP Transport v1

## Overview

This directory implements the version 1 HTTP transport layer using
FastAPI. It provides the streaming endpoint interface for socket
packet communication between clients and the server in an asynchronous
fashion.

## Filesystem Overview

| Location           | Description                                |
| ------------------ | ------------------------------------------ |
| [stream](./stream/) | FastAPI streaming transport implementation |

## Transport Architecture

The core component is the `populate(app)` function which mounts the
FastAPI router responsible for the streaming endpoint at the URL
prefix `/v1/stream`. This organizes the transport to support versioning
and modular extensibility.

The streaming endpoint manages long-lived HTTP connections, allowing
asynchronous bidirectional packet streams to flow between clients and
the server.

## Integration with Stream Module

The separate `stream` submodule encapsulates:

- The FastAPI `APIRouter` exposing the streaming endpoint
- Management of client sessions capturing state and lifecycle
- Packet serialization and streaming control logic via async generators
- Dependency injection of lifecycle hooks for connection,
  packet, and disconnect events

This separation enforces a clean modular structure and clear
responsibilities.

## Onboarding Approach

For new developers, start with understanding FastAPI routing and
`StreamingResponse` for HTTP streaming. Familiarity with Python
asyncio concurrency primitives such as tasks, events, and queues is
mandatory.

Next, examine the client session abstraction to understand its role
in holding outgoing packets and controlling connection death.

Study the packet structure and significance of packet types, especially
how the stream termination is triggered.

Review the dependency injection hooks for extensible lifecycle event
management.

Trace the streaming async generator to see how packets are emitted
and connection lifecycles are managed asynchronously.

This knowledge will provide a solid grasp of the transport's behavioral
model.

## Usage

Include the `populate(app)` function within your FastAPI application
setup to register the streaming routes under `/v1/stream`. This
integration exposes the streaming transport capabilities.

---

This module forms the foundational HTTP streaming transport layer of
the ReasonChip server architecture using FastAPI asynchronous APIs.
