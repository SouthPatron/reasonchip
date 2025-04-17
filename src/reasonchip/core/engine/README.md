# Engine

## Overview

This directory contains the core components of the ReasonChip Engine. It is
responsible for loading, validating, and running pipelines of tasks. Pipelines
are collections of tasks that define processing flows, including invoking
chips, dispatching to other pipelines, looping, and conditional execution.

The Engine manages pipeline loading, singleton facilities, the main execution
loop, and the registry of available chips.

## Filesystem Overview

| Location          | Description                         |
|-------------------|-----------------------------------|
| [context](./context/)       | Variable and flow control context classes |
| [facilities.py](./facilities.py) | Singleton facilities management           |
| [pipelines.py](./pipelines.py)   | Pipeline parsing, task definitions, and loading |
| [processor](./processor/)   | Core processor for running tasks        |
| [registry.py](./registry.py)     | Registration and loading of chip functions |
| [parsers](./parsers/)       | Parser utilities for expression evaluation |

## Key Concepts

### Engine

The `Engine` class manages the lifecycle of pipeline collections. It loads
pipeline YAML files, validates them (checking for missing pipelines or chips),
and runs specified pipeline entry points asynchronously. It leverages the
`Processor` to execute tasks.

### Pipelines and Tasks

Pipelines are lists of tasks which can include:

- `TaskSet`: a nested set of tasks
- `DispatchPipelineTask`: dispatch to another pipeline
- `ChipTask`: invoke a registered chip function
- `ReturnTask`: return a result and stop execution
- `DeclareTask`: declare variables
- `CommentTask`: ignored
- `TerminateTask`: forcibly terminate execution

Tasks support conditional execution, looping, and storing results.

The `PipelineLoader` loads pipelines recursively from directories, parsing YAML,
validating syntax and task types.

### Chip Registry

The `Registry` holds the registered chips—functions implementing specific
processing logic. Chips must have one Pydantic request model parameter and return
a Pydantic response model.

Chips can be registered manually or loaded dynamically from defined search
paths. The registry supports name-based lookup with fallback module prefixing.

### Facilities

The singleton `Facilities` class currently provides a singleton placeholder to
support any shared resources or global facilities the engine needs.

## Error Handling

Validation and runtime errors use custom exceptions with explicit error
messages. Pipeline and chip non-existence is checked eagerly in validation.
Parsing failures are wrapped to provide source context.

## Logging

All modules use Python logging extensively to provide debug, info, warning, and
error messages for tracing loading, validation, execution, and errors.

## Asynchronous Execution

Pipeline execution is asynchronous to support concurrency and awaitable chip
functions.


## Integration with Submodules

- `processor`: Executes the defined pipelines and tasks.
- `registry`: Manages chip loading and lookup.
- `pipelines`: Parses and validates pipeline definitions.

---

No other subdirectories exist here beyond those listed.
