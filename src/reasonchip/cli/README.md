# Command Line Interface

## Overview

This directory contains the main command line interface (CLI) entry
point for the ReasonChip project. It is responsible for parsing
command line arguments, instantiating the appropriate command objects
from the subcommands implemented in the `commands` subdirectory, and
orchestrating command execution.

The CLI supports both synchronous and asynchronous commands, sets up
logging configuration, and manages process naming for user clarity.

## Filesystem Overview

| Location           | Description                                  |
| ------------------ | -------------------------------------------- |
| [commands](./commands/)  | Implementations of individual CLI commands |
| [reasonchip.py](./reasonchip.py) | The main CLI executable and argument parser  |

## Onboarding Approach

1. Understand Python `argparse` for command line argument
   parsing, including subparser usage for subcommands.

2. Review the `main()` function in `reasonchip.py` for the general
   CLI execution flow: argument parsing, logging setup, command
   dispatch.

3. Dive into the `commands` subdirectory to examine individual command
   classes implementing the subcommands. Understand the interface
   they implement (`build_parser()`, `main()` or `async main()`).

4. Study how synchronous vs asynchronous command classes are handled.

5. Understand the `configure_logging()` usage to initialize logging
   levels from CLI arguments.

6. Get familiar with `setproctitle` to set the CLI process title to the
   invoked subcommand.

7. Understand the design decision for separating command execution
   logic into classes, supporting extensibility and modularity.

## CLI Execution Flow

The CLI initializes an `argparse.ArgumentParser` with subcommands
provided by the command classes. Each command builds its own
argument parser subtree. When invoked, the CLI:

- Parses arguments using the generated parser,
- Configures logging according to parsed log level arguments,
- Instantiates the command object,
- Sets process title to reflect the command being run,
- Delegates execution to the command object's `main()` method,
  awaiting if asynchronous,
- Returns the exit code from the command.

This structure allows the CLI to cleanly separate argument management,
logging, and command implementation.

---