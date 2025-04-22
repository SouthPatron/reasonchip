# Broker Service

## Overview

This directory contains the broker service component of ReasonChip. The
broker manages connections from clients and workers via specified
transports, coordinates task dispatch from clients to available workers,
and handles routing of messages between them. This service ensures
connection lifecycle management, worker capacity tracking, and reliable
packet forwarding.

The subcomponents include the Broker, which manages transports and
connections, and the Switchboard, which orchestrates routing, tracks
routes, and enforces protocol semantics.

## Filesystem Overview

| Location                 | Description                                       |
| ------------------------ | ------------------------------------------------ |
| [broker.py](./broker.py) | Broker class managing connections and transports|
| [switchboard.py](./switchboard.py) | Switchboard class handling routing of client-worker payloads |

## Onboarding Approach

To understand this directory, start with the `Broker` class in
`broker.py`. It initializes client and worker transports, tracks active
connections with concurrency-safe structures, and delegates per-packet
processing to the `Switchboard`. The broker handles lifecycle events
(start, stop), accepts new connections, demultiplexes incoming packets
from clients and workers, and manages connection termination.

Next, study the `Switchboard` in `switchboard.py`, which manages per-task
Routes that bind client requests to worker connections. It tracks route
state, manages worker availability, and ensures correct routing of payloads
for client RUN and CANCEL requests, and worker REGISTER and RESULT responses.

Understand the communications protocol via `SocketPacket` (from the
`protocol` package), which includes packet types and result codes used
throughout. Familiarity with async programming, concurrency control with
`asyncio.Lock`, UUID usage for connection and task IDs, and basic server
transport abstraction are necessary to fully grasp control flow.

## Component Responsibilities

- **Broker:** Acts as the connection manager, starts/stops transports,
  handles incoming client and worker connections, keeps track of
  connection associations, and routes incoming packets to the switchboard.

- **Switchboard:** Maintains routing of tasks between clients and workers.
  Implements task lifecycle: accepting RUN commands from clients,
  assigning them to available workers, handling worker registration and
  results, notifying clients of worker failure, and managing route cleanup.

- **Routing and State Management:** Switchboard keeps route records keyed
  by a UUID cookie per task, mapping client connections with worker
  connections. Available worker connections are tracked via a queue. The
  Switchboard serializes modifications through a single asyncio lock.

- **Packet Handling:** Different packet types trigger different
  code paths, following a request-response pattern. Unsupported or malformed
  packets are handled gracefully with error responses to the client.

## Concurrency and Safety

Both Broker and Switchboard use `asyncio.Lock` to protect shared
collections like connection maps and route lists to ensure thread-safe
access in an asynchronous environment. The Broker guarantees no
connection ID collisions and notifies Switchboard of connection state
changes. The Switchboard manages complex routes ensuring correct cleanup
on client or worker disconnects.

## Logging

Extensive logging is present for lifecycle events, connection events,
routing decisions, and error conditions to facilitate debugging and
monitoring.

## Extensibility

The design cleanly separates transports, connection management, and
routing. The routing logic can be extended in `Switchboard` to support
additional packet types or routing policies without impacting the Broker's
connection handling logic.

## Summary

The Broker module implements a scalable, asynchronous message routing
service coordinating clients and workers with robust state management,
connection lifecycle handling, and error reporting, based on strict
asynchronous protocols and concurrency control.
