# LocalRunner Utility

## Overview

This directory contains the `LocalRunner` utility which provides a simple,
local execution interface for the core pipeline engine. It initializes the
engine with specified collections of pipelines and manages variable scopes
for pipeline runs.

## Filesystem Overview

| Location           | Description                                         |
| ------------------ | ------------------------------------------------- |
| local_runner.py    | Implements the LocalRunner class for local pipeline execution |

## Onboarding Approach

A new developer should first understand the core pipeline engine concepts
located in `core.engine.engine` and `core.engine.variables`. These provide
API for pipeline executions and variable context management.

The `LocalRunner` class composes an `Engine` instance and a `Variables` set
of default variables. On creation, it initializes the engine with the given
pipeline collections.

To understand the code flow:

1. Review the `Engine` class and how it initializes with pipeline collections.
2. Look into the `Variables` class that handles variable storage and merging.
3. Study the `run` coroutine in `LocalRunner` which merges variables and triggers
   the engine's async run method.
4. Understand the `shutdown` method to cleanly terminate the engine.

Familiarity with asynchronous Python and pipeline execution models is required.

## Design and Responsibilities

`LocalRunner` acts as a facade to the core engine, managing:

- Engine lifecycle: initialization with pipeline collections and shutdown.
- Default variables context, merged with runtime overrides per execution.
- Asynchronous execution of pipelines by name with appropriate variables.

This class simplifies local or test usage of the engine without needing to
handle engine lifecycles externally.

Variable management uses the `Variables` abstraction to create isolated,
copyable contexts ensuring thread-safe operation.

`LocalRunner` directly depends on core engine modules but isolates local
execution details from higher-level application logic.

No other significant modules or components exist in this directory.

The directory acts as a utility layer for easy local pipeline interactions.
