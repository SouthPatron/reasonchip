# CLI Command Framework

## Overview

This directory defines the extensible command-line interface (CLI)
command infrastructure and built-in ReasonChip executable commands.
Commands provide high-level entrypoints for: launching brokers,
starting engine worker processes, running pipelines remotely,
or executing them locally.

Commands are implemented as subclasses of BaseCommand/AsyncCommand
abstract base classes, encapsulating parsing, argument validation,
and main operational logic. This decouples shared concerns (option
handling, logging, SSL configuration, exit code policies) from
command-specific orchestration logic.

## Filesystem Overview

| Location                        | Description                                                    |
| ------------------------------- | -------------------------------------------------------------- |
| [command.py](./command.py)      | BaseCommand/Command/AsyncCommand abstraction and common parser/option mixins |
| [exit_code.py](./exit_code.py)  | Standardized ExitCode enum for CLI command outcomes             |
| [broker_command.py](./broker_command.py)   | Implements BrokerCommand for running a ReasonChip broker server |
| [worker_command.py](./worker_command.py)   | Implements WorkerCommand for launching an engine process        |
| [run_command.py](./run_command.py)         | Implements RunCommand for running a pipeline remotely           |
| [run_local_command.py](./run_local_command.py) | Implements RunLocalCommand for local execution of pipelines     |

## Onboarding Approach

1. Start by reviewing `command.py` for the abstractions:
   - `BaseCommand` exposes a class-based contract (e.g., `command()`,
     `help()` and `description()`) for all CLI commands.
   - `build_parser()` pattern provides unified and extendable option
     schema including default logging flags and SSL/TLS argument groups.
   - `Command` and `AsyncCommand` separate synchronous and asynchronous
     execution flows via abstract `main()` methods.
2. Study `exit_code.py` for familiarization with all explicit exit
   codes used in error handling.
3. Review command implementations, which all follow similar structure:
   - Provide CLI argument group registration in `build_parser()` using
     inherited helpers for logging and SSL options as required.
   - Implement an async `main()` (except in `Command`, sync) for
     command logic; typical pattern is to parse inputs, produce/consume
     network transports if necessary, delegate core execution to engine/
     runner/task/remote client objects, and handle error conditions.
   - All commands consistently use ReasonChip exceptions for internal
     errors and fall back to traceback for unhandled conditions.
   - Shutdown procedures coordinate via asyncio events and signals.
4. To extend, implement a subclass of Command/AsyncCommand, register
   in `__init__.py`, and add to the output of `get_commands()`.

Developers should be comfortable with: Python's argparse, asyncio,
networking concepts, SSL/TLS settings, ReasonChip's core engine and
transport abstractions, and error signaling idioms.

## Command Composition Model

- Each command serves as an invocable entrypoint, providing argument parsing,
  execution, and error mapping. Command-specific logic is invoked in
  `main(args: argparse.Namespace, rem: typing.List[str])`.
- Network-related commands provide --log-level (for per-logger or global
  adjustment), and SSL options for transport security (client/server side).
- Commands are intended to be standalone, user-facing, and suitable for
  orchestration or scripting via predictable exit codes defined in `ExitCode`.

## SSL/TLS Configuration

- The abstract base class provides add_ssl_client_options and add_ssl_server_options.
  These inject argument groups (client/server PEM, CA, ciphers, version, options)
  into the CLI and are handled with ReasonChip's SSL context utilities.
- Parsed options are passed to transport factories or network initializers.
  Validation is deferred until transport instantiation.

## Logging and Consistent Exit Codes

- All commands support a --log-level CLI flag supporting both global
  and logger-specific granularity (DEBUG, INFO, etc.).
- All command failures or recoverable errors should use ExitCode to
  ensure shell scripts and callers can react to precise termination semantics.

## Signal-driven Shutdown (Broker/Worker)

- Broker and Worker command implementations use asyncio Events and
  signal handling to coordinate controlled shutdown. On receipt of
  SIGINT/SIGTERM/SIGHUP, async event is set to allow loops and network
  objects (Broker, TasksManager) to clean up and return gracefully.

## Command Registration

- All exposed and supported commands must be imported into `__init__.py`.
  They are made available via the `get_commands()` function for main CLI
  entrypoints to enumerate and dispatch to.

---

This CLI framework provides a consistent interface layer for ReasonChip's
executable tools and can be extended by implementing additional
Command/AsyncCommand subclasses following this contract.