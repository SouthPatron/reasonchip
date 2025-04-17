# HTTP Transport Common

## Overview

This directory contains the common HTTP transport components for ReasonChip. It
provides foundational types and abstractions used across various HTTP transport
implementations, including client session management and lifecycle callbacks.

## Filesystem Overview

| Location                    | Description                                  |
| --------------------------- | -------------------------------------------- |
| [common.py](./common.py)    | Core client session dataclass and callback hooks |
| [fastapi/](./fastapi/)      | FastAPI-based HTTP transport implementation  |

## Core Concepts

- **ClientSession**: Represents an individual client connection with a unique
  ID, an asyncio event to signal session termination, and a queue to hold outgoing
  packets.

- **CallbackHooks**: Holds user-provided asynchronous callbacks for connection
  lifecycle events: new client connection, incoming data packet, and client
  disconnection.

These components facilitate decoupling of transport-level connection handling
from business logic, enabling different HTTP transport implementations to use
common session and callback interfaces.

---

The module imports ReasonChip `SocketPacket` and `PacketType` for packet handling.
Logging is initialized but usage depends on implementations consuming these types.

The directory acts as a bridge between the generic transport core and concrete
HTTP server implementations like FastAPI.
