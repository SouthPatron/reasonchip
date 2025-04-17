# Command Line Interface

## Overview

This directory contains the entrypoint and main CLI interface for the
ReasonChip project. It defines the top-level command dispatcher that
parses command-line arguments, configures logging, manages process
identity, and delegates execution to specific commands implemented in
submodules.

## Filesystem Overview

| Location       | Description                                                   |
| -------------- | ------------------------------------------------------------- |
| [commands](./commands/) | Contains implementations of individual CLI commands     |
| reasonchip.py  | Top-level CLI entrypoint, argument parsing and dispatching    |

## CLI Entry Point

The core executable `reasonchip.py` sets up an `argparse` parser
with subcommands representing the available CLI operations.

Each command implements methods to describe itself and build its
specific argument parser. The main entry point loads these commands,
constructs the subcommand argument tree, and executes the selected
command.

Logging configuration is applied early based on CLI options. The
process title is set for system utilities visibility. Commands are
dispatched synchronously or asynchronously depending on their
implementation.

Exit codes from commands are consistently returned, enabling scripting
and automation.

---

This README serves as a guide for developers working in the CLI
interface layer, facilitating understanding of how command dispatch and
argument management are architected in ReasonChip.
