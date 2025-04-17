# Client API and Connection Management

## Overview

This directory contains the client-side implementation of the communication
layer for ReasonChip. It manages multiplexed connections to a remote engine
via network transport, provides an API to run pipelines, and handles packet
sending and receiving asynchronously.

## Filesystem Overview

| Location           | Description                              |
|--------------------|----------------------------------------|
| [api.py](./api.py)               | High-level API for running pipelines asynchronously |
| [client.py](./client.py)         | Client connection management and packet send/receive |
| [multiplexor.py](./multiplexor.py) | Multiplexor managing multiple logical client connections over a single transport |

## Multiplexor

The Multiplexor encapsulates management of one underlying transport client
connection (ClientTransport), and multiplexes multiple logical client
connections. Each logical connection is identified by a UUID called connection_id.

- Registers and releases logical connections asynchronously.
- Maintains queues for incoming packets per connection.
- Routes incoming packets from transport to appropriate client queues.
- Manages association of cookies to connections.
- Handles stopping and cleanup including notifying clients of broker
disconnection.

It uses an asyncio lock to ensure thread-safe access to its shared state.

## Client

Client acts as a context manager abstracting a logical connection. It:

- Registers itself with the Multiplexor upon enter.
- Releases connection on exit.
- Provides methods to send packets and receive packets asynchronously.
  Incoming packets are retrieved from the queued packets of the logical
  connection.
- Maintains a unique UUID "cookie" used to identify the logical session.

## API

The Api class provides a higher-level asynchronous interface:

- Uses Client instances to manage logical connections.
- Provides run_pipeline method to execute a named pipeline with optional
  variables and cookie.
- Handles sending RUN packet requests and receives streamed packets until
  a RESULT or CANCEL response is received.
- Manages connection errors and cancellation requests.

Logging is used extensively across all modules for debugging and tracking
packet flow.

This directory thus abstracts multiplexed asynchronous communication with
the ReasonChip engine for client-side usage.