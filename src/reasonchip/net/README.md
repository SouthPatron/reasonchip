# Networking Layer

## Overview

This directory contains the networking layer for ReasonChip, which
facilitates communication between distributed components. It implements
three key roles:

- **Broker:** Coordinates connections from clients and workers,
routing tasks and results.
- **Client:** Provides the Python-native API and multiplexed connection
management for submitting pipeline runs.
- **Worker:** Manages concurrent execution of ReasonChip pipelines,
handling task multiplexing and network communication.

The transport protocols over which these components communicate are
implemented separately in the `transports` subdirectory.

## Filesystem Overview

| Location          | Description                             |
| ----------------- | ------------------------------------- |
| [broker](./broker/)   | Broker service handling routing and connection management |
| [client](./client/)   | Client API and multiplexed connection management |
| [transports](./transports/) | Transport implementations for TCP, gRPC, HTTP, UNIX sockets and SSL configurations |
| [worker](./worker/)   | Worker tasks multiplexing pipeline execution on network transports |

## Onboarding Approach

Start by understanding the key network roles:

1. **Broker:**  Study the `Broker` and `Switchboard` classes in
   `broker/`. The Broker manages client and worker connections,
   while the Switchboard handles routing packets and tasks between
   them.

2. **Worker:**  Review the `TaskManager` in `worker/`, which handles
   concurrent pipeline runs through asynchronous task multiplexing
   and communicates results back over network transports.

3. **Client:** Understand the multiplexed connections in
   `client/` (`Multiplexor`, `Client` classes) and the high-level
   `Api` interface that submits pipeline execution requests and
   collects results asynchronously.

4. **Transports:** Learn the transport abstraction layer in
   `transports/`, which defines uniform client and server transports
   over TCP, gRPC, HTTP, and UNIX sockets. This layer handles
   packet serialization, connection management, and SSL/TLS
   configuration.

Grasp the common packet communication protocol via
`SocketPacket`, `PacketType`, and `ResultCode` defined in
`net/protocol.py`. All roles exchange these packets via transport
transports. Deep familiarity with asyncio concurrency, async network
streams, queue multiplexing, and UUID-based session and task IDs is
required to understand message lifecycles and flow.

## Networking Protocol and Packets

The core communication uses `SocketPacket` instances comprising
packet type, optional task UUID cookie, pipeline and variable data,
result codes, and errors. Packet types include REGISTER (worker
capacity), RUN (client task request), CANCEL, RESULT, and SHUTDOWN.

Serialized over transports with length-prefixed JSON messages,
packets enable a clean, extensible protocol for executing pipelines
remotely with robust error and cancellation reporting.

## Architecture

- The **Broker** acts as the connection manager and router, maintaining
  active client and worker connections, delegating incoming packets
  for routing and task assignment to the Switchboard.

- The **Switchboard** serializes task routing with concurrency control
  locks, matches RUN requests from clients to available workers,
  tracks active routes by task cookie, and forwards results, errors,
  and cancellations appropriately.

- The **Worker** asynchronously multiplexes multiple concurrent pipeline
  runs via asyncio Tasks, manages cancellation and shutdown,
  and reports results via transport.

- The **Client** multiplexes logical client sessions over a single
  transport connection, manages packet queues per connection, and
  exposes a high-level API to run pipelines and receive streamed
  results asynchronously.

- The **Transports** provide asynchronous client and server implementations
  abstracting the underlying protocol and socket details. They provide
  safe concurrent send, receive, connection lifecycle management, and
  SSL/TLS security.

## Summary

This networking layer encapsulates a distributed asynchronous system
for ReasonChip pipeline execution with clear separation between roles,
solid concurrency and lifecycle management, a clean packet protocol,
protocol-independent transport abstractions, and pluggable secure
transports. It facilitates remote pipeline execution with concurrency,
cancellation, and real-time result streaming.
