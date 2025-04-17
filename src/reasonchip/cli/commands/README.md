# CLI Commands

## Overview

This directory contains the implementation of the CLI commands used
in the ReasonChip project. These commands include launching brokers,
running pipelines (locally and remotely), and launching worker engines.

The commands are structured as classes inheriting from base command
interfaces supporting synchronous and asynchronous execution.

## Filesystem Overview

| Location                  | Description                                   |
| ------------------------- | ---------------------------------------------|
| [command.py](./command.py)         | Base classes and utilities for CLI commands       |
| [exit_code.py](./exit_code.py)         | Common exit codes enumeration                       |
| [broker_command.py](./broker_command.py)   | Command to start a broker server                    |
| [worker_command.py](./worker_command.py)   | Command to start a worker engine                     |
| [run_command.py](./run_command.py)         | Command to run a pipeline remotely via a broker      |
| [run_local_command.py](./run_local_command.py) | Command to run a pipeline locally                      |
| [__init__.py](./__init__.py)                | Aggregates command classes and exports API           |

## Command Architecture

Commands extend from `BaseCommand`, implementing required
methods for:

- `command()` returning the command string
- `help()` returning a brief help description
- `description()` returning a more detailed description
- `build_parser()` to assemble command-specific CLI arguments
- `main()` or `async main()` as the entry point for the command.

Common argument options like logging levels and SSL settings are
provided as reusable class methods in `BaseCommand` to ensure
consistency across commands.

## Core Commands

- **BrokerCommand**: Runs a ReasonChip broker coordinating between
  engines (workers) and clients. Supports multiple listeners and
  SSL settings, handles signal-based shutdown.

- **WorkerCommand**: Runs a worker engine process to perform tasks
  assigned by the broker. Manages pipeline collections and parallel
  task count. Uses SSL to communicate with broker securely.

- **RunCommand**: Connects as a client to a broker and runs a
  specified pipeline remotely with variable inputs. Outputs JSON
  response.

- **RunLocalCommand**: Executes a pipeline locally without broker
  involvement, using a local runner. Supports variable inputs.

## Error Handling

All commands utilize the `ExitCode` enum to consistently indicate
success or failure states. Exceptions from ReasonChip core raise
logged errors and return a generic error exit code. Unexpected
exceptions are logged with traceback information.

## Signal Management

Broker and Worker commands install signal handlers for SIGINT,
SIGTERM, and SIGHUP to perform graceful shutdown by setting internal
asyncio events which trigger termination.

## SSL/TLS Support

Commands support both client and server SSL option groups including
certificate paths, key files, CA verification, cipher lists, and
TLS versions. SSL contexts are built as needed and applied to
underlying transport connections.

---

This README provides an overview for developers to understand current
command implementations, argument parsing conventions, and integration
points with the ReasonChip runtime architecture.
