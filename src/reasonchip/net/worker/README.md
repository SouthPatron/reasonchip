# Worker

## Overview

This directory contains the TaskManager which manages multiple concurrent
engine tasks over a transport connection to a server. It handles
incoming packets, task lifecycle, and communication with the server
using a packet-based protocol.

## Filesystem Overview

| Location                     | Description                                           |
| ----------------------------| -----------------------------------------------------|
| [task_manager.py](./task_manager.py) | Manages engine tasks, communication, and multiplexing |

## TaskManager

The TaskManager is the central component managing multiple engine
execution tasks concurrently. It receives commands via the transport
layer, dispatches engine runs, cancels running tasks, and manages
clean shutdown.

### Key Responsibilities

- Establish and maintain connection with the server transport.
- Receive and process packet commands (RUN, CANCEL, SHUTDOWN).
- Manage concurrent execution of engine tasks with a maximum capacity.
- Serialize and report engine run results or exceptions back to the server.
- Gracefully handle shutdown and cancellation requests.

### Multiplexing

Uses an asyncio event loop to multiplex between:

- Incoming packets queue.
- Task completion events.
- Shutdown signal.

### Task Execution

Each RUN command launches a new asynchronous task to run the engine
with provided pipeline and variables. Tasks are tracked by a UUID
cookie.

### Error Handling

Exceptions in engine runs are caught and reported to the server with
associated error and stack trace.

### Protocol

Uses a packet-based protocol with defined packet types:

- REGISTER: Sent on startup to declare capacity.
- RUN: Command to execute a pipeline.
- CANCEL: Command to cancel a running task.
- SHUTDOWN: Command to stop all processing.
- RESULT: Sent back with the outcome of a task.

