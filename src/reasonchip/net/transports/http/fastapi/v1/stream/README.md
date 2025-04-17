# FastAPI Stream Transport

## Overview

This directory implements the FastAPI-based streaming transport
layer for socket packet communication. It defines the streaming
endpoint that handles client connections for continuous packet
exchange using asynchronous streaming responses.

## Filesystem Overview

| Location                            | Description                                      |
| --------------------------------- | ------------------------------------------------ |
| [stream.py](./stream.py)           | FastAPI router and streaming endpoint logic       |

## Streaming Endpoint Details

The streaming endpoint `/stream` uses FastAPI's `StreamingResponse`
for asynchronous bidirectional communication.

- A `ClientSession` instance tracks connection state and
  manages outgoing packet queues and death signals.

- On connection, the new client session is registered via
  dependency-injected callback hooks.

- The initial client-sent `SocketPacket` is processed immediately.

- An async generator `log_stream` yields encoded packets
  continually from the session's outgoing queue.

- The generator listens for session death and terminates streaming
  once a `RESULT` type packet is emitted or death signal is set.

- Proper cleanup on disconnect is ensured via disconnect callback.

## Dependency Injection

The module leverages dependency injection for callbacks handling
connection lifecycle events such as new connections, packet reads,
and client disconnects.

## Packet Handling

Packets rely on a `SocketPacket` model representing structured
socket data. Packet types influence streaming control flow
(e.g., when a RESULT type terminates streaming).

## Logging and Error Handling

Exception logging within the streaming generator aids debugging
potential runtime issues.

---

This module forms a core component of client-server streaming
transport under the FastAPI HTTP transport stack.