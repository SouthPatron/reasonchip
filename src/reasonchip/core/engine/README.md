# Engine

## Overview

The `engine` directory contains the core runtime components for 'ReasonChip'.
It orchestrates the processing and execution of pipelines, tasks, and chips.
The submodules include pipeline parsing and loading, variable interpolation and
management, flow control for task execution, chip function registry and dynamic
loading, and the main processor that runs the tasks accordingly.

## Filesystem Overview

| Location                 | Description                                   |
|--------------------------|-----------------------------------------------|
| [engine.py](./engine.py)              | Core Engine managing lifecycle, pipeline loading, initialization, and validation.
| [variables.py](./variables.py)        | Variables class manages variable storage, interpolation, safe evaluation.
| [registry.py](./registry.py)          | Registry manages chip function registration and dynamic module loading.
| [parsers.py](./parsers.py)            | Safe evaluation and escaping helpers for expressions.

## Onboarding Approach

A new developer should start by understanding the pipeline structure in
`pipelines.py`. This module defines the data models representing
various task types (e.g., TaskSet, ChipTask, DispatchPipelineTask) and the
Pipeline container. The PipelineLoader loads YAML pipelines and validates
task structures.

Next, study the `engine.py` core class, `Engine`. It loads pipelines
through PipelineLoader, maintains a dictionary of pipelines, validates pipelines
by checking referenced chips and nested flows, and exposes an async `run` method
which instantiates Processor and delegates execution.

The `processor.py` module is where the runtime execution occurs. The Processor
takes care of looping, condition evaluation, variable scoping, and delegates to
appropriate handlers for the various task types such as ChipTask, DispatchPipelineTask,
etc. It runs tasks asynchronously and manages results.

Variable management is done through the `variables.py` module. Variables supports
hierarchical paths, deep updates, and interpolation in strings using embedded
Jinja-like braces (`{{ expr }}`). It uses a safe evaluator in `parsers.py` to
prevent malicious code execution during interpolation.

The `flow_control.py` module encapsulates the task sequence queue and provides basic
queue operations for the Processor.

The `registry.py` module provides a global registry of chip functions. Chips are defined
as async functions annotated with Pydantic request/response models. Registry supports
dynamic import and scanning of modules and chipsets.

To fully understand the codebase, the developer should be familiar with asynchronous
programming in Python, Pydantic models, YAML parsing, safe code evaluation techniques,
Python typing and generics, and basic compiler/interpreter concepts such as AST parsing
and evaluation.

## Task Types and Pipeline

Tasks fall into several categories:
- **TaskSet**: group of tasks that can execute serially or async, with own variables.
- **DispatchPipelineTask**: invokes a named pipeline, effectively nested execution.
- **ChipTask**: wraps an invocation of a registered chip function.
- **DeclareTask**: declares variables.
- **ReturnTask**: returns from a pipeline with a value.
- **CommentTask** and **TerminateTask**: for comments and explicit termination.

Loops and conditional execution (`when`) are supported at the task level.

## Variable Interpolation and Safe Evaluation

Variables supports accessing nested attributes via dot/bracket notation.
Interpolation uses embedded expressions wrapped in `{{ }}`, which are safely
evaluated using a restricted `eval` context exposing controlled builtins and
the current variable map. Recursive interpolation supports lists, dicts, and strings.

## Error Handling and Validation

Validation occurs at pipeline load time, checking all referenced pipelines and chips
exist and all tasks parse correctly. Runtime exceptions are structured into custom
exceptions for clear failure points.

## Asynchronous Execution

Processor supports asynchronous chip invocation and task sets.
Looping constructs provide iteration context variables analogous to Jinja loops.

