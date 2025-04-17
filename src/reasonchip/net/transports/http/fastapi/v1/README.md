# FastAPI HTTP Transport v1

## Overview

This directory implements the version 1 HTTP transport layer using
FastAPI. It primarily provides the streaming endpoint interface
for socket packet communication between clients and the server.

## Filesystem Overview

| Location                   | Description                               |
| -------------------------- | ----------------------------------------- |
| [stream](./stream/)        | FastAPI streaming transport implementation |

## Transport Structure

The transport is organized to support extensibility and clear
separation of concerns. The main `__init__.py` exposes a function
`populate(app)` that integrates FastAPI routers defined in
submodules.

The streaming transport under `/v1/stream` handles
long-lived HTTP connections for real-time packet streams.

## Integration with Stream Submodule

- The `populate` function calls FastAPI's
  `include_router` to mount the streaming router.

- The stream module defines the actual FastAPI endpoints,
  the client session lifecycle, and packet streaming logic.

- Versioning is embedded in the URL prefix `/v1/stream` to
  support potential future upgrades.

## Usage

Include this module's `populate` function in your FastAPI
application setup to register the necessary streaming routes.

---

This module is a foundational part of the ReasonChip server's
HTTP transport stack utilizing FastAPI asynchronous streaming.
