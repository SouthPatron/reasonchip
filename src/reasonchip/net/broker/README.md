# Broker Service

## Overview
This directory contains the broker service of the ReasonChip system. The broker is responsible for managing connections from clients and workers, dispatching job requests from clients to available workers, and handling communication and routing of messages between them. It serves as the central coordinator that maintains connection states, routes payloads, and manages worker capacity.

## Filesystem Overview

| Location           | Description                               |
| ------------------ | ----------------------------------------- |
| [broker.py](./broker.py)       | Main Broker class managing transports and connections |
| [switchboard.py](./switchboard.py) | Switchboard class handling routing logic between clients and workers |
| [__init__.py](./__init__.py)   | Package initialization, exports Broker |

## Components

### broker.py
- Defines the `Broker` class that:
  - Manages client and worker transports.
  - Starts and stops server transports for clients and workers.
  - Maintains connection mappings and synchronization with asyncio locks.
  - Delegates incoming packets from clients and workers to the `Switchboard`.
  - Sends packets to connections asynchronously.

### switchboard.py
- Defines the `Switchboard` class that:
  - Maintains routing tables linking clients and workers via unique route IDs.
  - Tracks availability of worker connections.
  - Handles client packets such as `RUN` and `CANCEL`.
  - Handles worker packets such as `REGISTER` (capacity) and `RESULT`.
  - Handles client and worker disconnections and cleans up routing info.
  - Sends appropriate responses back to clients.

### __init__.py
- Sets up the logger for this service.
- Exports the primary public interface, the `Broker` class.

## Notes
- The broker relies on the `ServerTransport` interface for network communication.
- All routing uses UUIDs as unique identifiers for connections and tasks.
- Asynchronous asyncio primitives are employed for concurrency control and communication.
- Logging is used extensively for connection lifecycle and route management.
- The switchboard design decouples path computation and routing from transport logic.


