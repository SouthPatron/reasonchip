# Worker

## Overview

This directory contains the worker components responsible for managing
concurrent execution of ReasonChip engine runs. It handles multiplexing
of tasks received from a network transport connection to a server.

The core component is the TaskManager, which interacts with the ReasonChip
Engine and a client transport to run multiple pipelines concurrently.

## Filesystem Overview

| Location                | Description                                |
|-------------------------|--------------------------------------------|
| [task_manager.py](./task_manager.py) | Implements TaskManager for engine task multiplexing |

## Onboarding Approach

Start by understanding ReasonChip's Engine concept as it is the core
computing unit executed by the TaskManager. Familiarize yourself with
`reasonchip.core.engine.engine.Engine` and how pipeline runs are
triggered.

Next, grasp the role of the transport abstraction, specifically
`ClientTransport`, which mediates packetized communication with the
server.

Then dive into the TaskManager class where asynchronous multitasking
patterns are heavily used (asyncio Tasks, Queues, Events). The
TaskManager multiplexes multiple concurrent engine runs and
coordinates their lifecycle including start, cancellation, and shutdown.

Be competent with asyncio concurrency: task creation, cancellation,
waiting, and multiplexing with queues and events.

Also understand the network packet model via `SocketPacket`, `PacketType`,
and how these packets drive control flow (RUN, CANCEL, SHUTDOWN).

## TaskManager Responsibilities

TaskManager maintains a maximum capacity of concurrent engine runs.
It connects to a server via transport and registers its capacity.

It listens for packets from the server: 
  * RUN packets create and start a new engine run async task.
  * CANCEL cancels running tasks identified by cookie.
  * SHUTDOWN stops the manager.

Each async engine run task runs the ReasonChip engine with provided
pipeline and variables, then sends back result or exception packets.

The manager creates and maintains Tasks handling the engine runs and
uses asyncio wait mechanisms to monitor their completion or cancellation.
TaskManager cleans up completed tasks and manages graceful shutdown.

## Error Handling and Logging

TaskManager logs extensively at debug and info levels for task
creation, completion, and packet processing.

It handles exceptions during engine runs by sending exception packets
back to the server with stack traces for diagnostics.

## Concurrency Model

Uses asyncio for concurrent asynchronous processing:

- Incoming packets placed on an asyncio.Queue.
- A multiplexing loop awaits incoming packets and task completions.
- Cancellation and shutdown signals are handled via asyncio.Event.
- Engine runs are executed as individual asyncio.Tasks.

## Summary

This worker module encapsulates multiplexed asynchronous execution of
ReasonChip engine pipelines on a networked client worker node. It is
a key part of the distributed architecture enabling remote pipeline
execution with concurrency, cancellation, and status reporting.