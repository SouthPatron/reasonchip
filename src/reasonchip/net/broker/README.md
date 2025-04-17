# Broker Service

## Overview
This directory contains the broker service of the ReasonChip system. The broker is responsible for managing connections from clients and workers, dispatching job requests from clients to available workers, and handling communication and routing of messages between them. It serves as the central coordinator that maintains connection states, routes payloads, and manages worker capacity.

## Filesystem Overview

| Location           | Description                               |
| ------------------ | ----------------------------------------- |
| [broker.py](./broker.py)       | Main Broker class managing transports and connections |
| [switchboard.py](./switchboard.py) | Switchboard class handling routing logic between clients and workers |

