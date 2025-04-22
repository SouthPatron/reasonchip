# CLI Commands

## Overview

This directory implements command-line interface commands for
ReasonChip. Commands include starting brokers and worker engines,
running pipelines remotely or locally, and managing shared
command logic.

Commands are classes derived from base Command or AsyncCommand.
They parse arguments, run the main logic asynchronously,
and define command metadata.

## Filesystem Overview

| Location                  | Description                                     |
| ------------------------- | -----------------------------------------------|
| [command.py](./command.py)         | BaseCommand and AsyncCommand abstract classes with common CLI argument groups |
| [exit_code.py](./exit_code.py)         | ExitCode enum for consistent CLI exit status codes |
| [broker_command.py](./broker_command.py)   | BrokerCommand runs the ReasonChip broker server for mediating engines and clients |
| [worker_command.py](./worker_command.py)   | WorkerCommand runs an engine process providing worker tasks to the broker |
| [run_command.py](./run_command.py)         | RunCommand runs a pipeline remotely via a broker connection |
| [run_local_command.py](./run_local_command.py) | RunLocalCommand runs a pipeline locally without a broker connection |
| [__init__.py](./__init__.py)                | Aggregates and exports available commands and utilities |

## Onboarding Approach

Start by understanding `BaseCommand` and `AsyncCommand` abstract
base classes in `command.py`. They define:

- Command metadata (`command()`, `help()`, `description()`)
- Argument parser construction (`build_parser()`)
- Common CLI option groups for logging and SSL/TLS client/server
  settings
- Asynchronous or synchronous `main()` method signature

Next, inspect `ExitCode` enum in `exit_code.py` for error code meanings.

For specific commands, examine:

- `BrokerCommand`:
  Sets up network listeners and server sockets to accept
  engine workers and clients. Manages signal handling for
  graceful shutdown.

- `WorkerCommand`:
  Instantiates an Engine object to load pipeline collections
  and registers worker capacity with the broker. Manages tasks
  asynchronously with signal-driven shutdown.

- `RunCommand`:
  Connects as a client to a broker, sets variables from CLI,
  then requests the execution of a pipeline remotely and outputs
  JSON results.

- `RunLocalCommand`:
  Runs pipelines locally without networking using the LocalRunner
  helper and variable management.

For networking, SSL option handling is integrated into parser
builders and transport creation.

Become familiar with asyncio, argparse, SSL contexts, and
ReasonChip engine abstractions (Engine, Variables, Multiplexor,
Api) for complete understanding.

## Command Structure

Commands encapsulate the lifecycle of CLI execution:

1. Declare CLI arguments including SSL and log options.
2. Run asynchronous `main()` serving as command entrypoint.
3. Establish networking via transports or local engine runner.
4. Handle errors using ReasonChip exceptions and fallback
   to logging unhandled exceptions.
5. Use asyncio events and signal handling for safe termination.

## SSL/TLS Integration

Commands provide reusable client and server SSL option groups for
certificate files, keys, CA bundles, cipher lists, TLS versions,
and verification options. These options are parsed and converted
into SSLContext objects by Command's helper methods and passed to
network transport factories.

## Logging and Exit Codes

Commands support a `--log-level` flag for adjusting logger
verbosity per logger namespace or globally. Exit codes are
standardized through `ExitCode` enum for CLI consumers.

## Signal Handling

Broker and Worker commands install asyncio signal handlers for
SIGINT, SIGTERM, SIGHUP that trigger internal events to coordinate
shutdown sequences.

---

This README summarizes the core CLI commands, how they integrate
with ReasonChip runtime, and provides a guide for developers to
navigate and extend the CLI command set reliably.