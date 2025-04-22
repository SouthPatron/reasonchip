# FastAPI HTTP Transport

## Overview

This directory contains the FastAPI HTTP transport implementation for
ReasonChip. It provides the configuration and setup of the FastAPI
application, middleware, dependency injection, and routes for the
HTTP transport layer.

## Filesystem Overview

| Location     | Description                         |
| ------------ | --------------------------------- |
| [fapi.py](./fapi.py) | FastAPI app setup and main entry point |
| [di.py](./di.py)     | Dependency injection utilities     |
| [v1/](./v1/)         | Version 1 API endpoints and logic  |

## Architecture

The FastAPI transport exposes a FastAPI application configured
in `fapi.py`. This includes middleware for CORS and response time
measurement and mounts versioned API routers (currently v1).

The `CallbackHooks` instance is attached to the app state and
accessible throughout request lifecycles via dependency injection
functions defined in `di.py`.

Versioned API modules (like `v1`) define the endpoints and route
handlers, separating transport versioning from app setup.

## Middleware

- Adds CORS middleware with an empty allow list.
- Adds a middleware that calculates the request processing time in
  microseconds and adds it as an `X-Process-Time` header.

## Dependency Injection

- Provides helpers to retrieve callback hooks from the app state.
  These are used by route handlers to hook into server-side logic.

## API Versioning

- The `fapi.py` module imports and mounts the version 1 API
  endpoints. This allows future versions to coexist and be managed
  cleanly.

---

This module is a core piece integrating the ReasonChip backend with
FastAPI's async HTTP capabilities.
