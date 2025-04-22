# FastAPI Stream Transport

## Overview

This directory provides a FastAPI-based streaming transport layer
implementation for socket packet communication. It exposes a single
streaming endpoint that manages client sessions and facilitates
asynchronous packet exchange over HTTP.

## Filesystem Overview

| Location           | Description                                 |
| ------------------ | ------------------------------------------- |
| [stream.py](./stream.py) | FastAPI router defining the streaming endpoint |

## Onboarding Approach

Start by understanding FastAPI routes and StreamingResponse.
Familiarity with asynchronous programming and asyncio primitives
like tasks, events, and queues is essential to grasp the
concurrent flow.

Next, examine the `ClientSession` abstraction which encapsulates
session state, the outgoing packet queue, and death signaling.
Understand how this controls the life cycle of client-server
communication.

Review the `SocketPacket` model that standardizes packet
structures and the role of packet types, especially the `RESULT`
type used to terminate streaming.

Become familiar with dependency injection in FastAPI, specifically
how callback hooks are injected to manage connection lifecycle
events like new connection registration, packet processing,
and disconnection cleanup.

Lastly, analyze the `log_stream` async generator in the streaming
endpoint to understand how outgoing packets are serialized and
yielded until completion or disconnection.

## Architecture and Behavior

A FastAPI `APIRouter` exposes a single POST `/stream` endpoint.
When a client connects, it creates a new `ClientSession` instance.
The session is registered, triggering the new connection callback.

The initial client packet is immediately processed via the read
callback. The endpoint then returns a `StreamingResponse` with an
async generator that listens for outgoing packets.

The generator concurrently waits for either a death signal or
packets on the session's outgoing queue. When a packet arrives,
it is serialized to JSON and streamed to the client.

If a packet of type `RESULT` is sent, the generator sets the death
signal and terminates the stream.

Exception handling and logging ensure that runtime errors in the
generator are caught and logged.

On termination, the disconnect callback is invoked for cleanup.

This design supports bidirectional, event-driven streaming over
HTTP in an asynchronous FastAPI context.

## Dependency Injection

The system relies on injected callback hooks for extensible
lifecycle management, supporting loosely coupled event handling
for new connections, incoming packets, and disconnects.

## Packet Model and Control Flow

`SocketPacket` represents the packet structure flowing through the
stream. Its `packet_type` guides streaming flow control, notably
terminating stream emission when a `RESULT` packet is received.

---

This directory implements a focused asynchronous streaming transport
layer for FastAPI HTTP stack supporting structured socket packet
communication with lifecycle event hooks and resource cleanup.