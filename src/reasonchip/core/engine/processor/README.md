# Processor Engine

## Overview

This directory contains the core processing engine responsible for running
and managing flows of tasks defined as pipelines. It executes different
kinds of tasks such as chip invocations, pipeline dispatches, loops,
and conditional runs according to given variables and flow control.

The processor is designed to asynchronously run complex task sets in a
sequential or concurrent manner while supporting variable scoping,
looping, conditional execution, and task result handling.

## Filesystem Overview

| Location                  | Description                                   |
|---------------------------|-----------------------------------------------|
| [./processor.py](./processor.py) | Core Processor class and task execution logic|

## Processor Responsibilities

- Runs a flow consisting of a series of tasks while managing variable
  scope and flow control.
- Supports conditional execution via "when" clauses on tasks.
- Supports looping over collections with loop metadata available to tasks.
- Handles task result storage and appending into variables.
- Executes tasks such as chip invocations, pipeline dispatches, task sets,
  declares, returns, comments, and termination.

## Task Types and Execution

- **ChipTask:** Invokes a registered chip with validated parameters.
- **DispatchPipelineTask:** Resolves and runs a named pipeline dispatch.
- **TaskSet:** Runs a set of tasks synchronously or asynchronously.
- **DeclareTask:** Declares new variables to be merged into the variable set.
- **ReturnTask:** Returns from the flow with a specified result.
- **TerminateTask:** Forces termination with a result.
- **CommentTask:** Skipped during execution.

## Looping

Any task that supports looping will be executed multiple times over an
iterable variable. Loop control variables like loop.index, loop.first,
loop.last, etc., are automatically set for each iteration.

## Task Result Storage

Tasks can specify the results to be stored directly into variables or
appended into list variables. Proper checking ensures appends are only
performed on list variables.

## Error Handling

Errors during task execution such as invalid parameters or missing
chips/pipelines raise specific exceptions. Nested exceptions are
wrapped to indicate task or pipeline context.

## Asynchronous Execution

Certain task types (TaskSet, DispatchPipelineTask, ChipTask) support
running asynchronously by creating asyncio tasks. The caller can then
await or retrieve results later.

## Integration

The Processor is instantiated with a resolver coroutine that resolves
pipeline names into Pipeline objects for dispatch tasks, enabling
plugin-like extensibility of task pipelines.

## Logging

Debug and info logs are provided throughout task execution, loop
iterations, and error cases for traceability and troubleshooting.

---

No other files or subdirectories exist here to document.

