# Local Runner

## Overview

This directory contains the `LocalRunner` component, which is a high-level
interface for running pipelines locally by leveraging the underlying engine
implementation. It initializes the engine with specified pipeline collections
and manages variable contexts for pipeline execution.

## Filesystem Overview

| Location          | Description                                |
| ----------------- | ------------------------------------------|
| `local_runner.py` | Defines the LocalRunner class responsible for running pipelines locally |

## LocalRunner Responsibilities

`LocalRunner` encapsulates the instantiation and management of the core engine
for local pipeline executions. It handles initialization by loading the given
pipeline collections and maintains a default set of variables that can be
overridden during each run.

- The constructor initializes the engine with specific collections and sets
  default variables.
- The `run` method executes a named pipeline asynchronously, merging default
  variables with any overrides provided.
- The `shutdown` method cleanly terminates the engine instance.

Logging is included to track key events like initialization, pipeline execution,
and shutdown for observability.

The `Variables` abstraction is used internally to manage variable contexts.

This module depends on the core engine and context modules from the parent
package for actual pipeline handling and variable management.