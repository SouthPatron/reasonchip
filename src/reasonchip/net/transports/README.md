# Transports

## Overview

This directory provides transport layer implementations for ReasonChip.
It includes client and server transports over various protocols such as TCP,
gRPC, UNIX sockets, HTTP, and facilities for configuring SSL/TLS.

It defines abstract base classes for client and server transports, concrete
implementations for each protocol, SSL option configurations, and utilities
for creating clients and servers based on URIs.

## Filesystem Overview

| Location                    | Description                                  |
| --------------------------- | -------------------------------------------- |
| [client_transport.py](./client_transport.py) | Abstract base class for client transports |
| [server_transport.py](./server_transport.py) | Abstract base class for server transports |
| [tcp_client.py](./tcp_client.py)    | TCP client transport implementation        |
| [tcp_server.py](./tcp_server.py)    | TCP server transport implementation        |
| [socket_client.py](./socket_client.py) | UNIX socket client transport implementation|
| [socket_server.py](./socket_server.py) | UNIX socket server transport implementation|
| [grpc_client.py](./grpc_client.py)  | gRPC client transport implementation       |
| [grpc_server.py](./grpc_server.py)  | gRPC server transport implementation       |
| [http_client.py](./http_client.py)  | HTTP client transport implementation (async HTTP with workers) |
| [http_server.py](./http_server.py)  | HTTP server transport implementation using Hypercorn and FastAPI  |
| [ssl_options.py](./ssl_options.py)  | Configuration dataclasses for SSL/TLS options for clients and servers |
| [utils.py](./utils.py)              | Utilities for transport construction and parsing address schemes |

## Concepts

### ClientTransport and ServerTransport

- Abstract base classes that define the contract for client and server transports.
- Clients support asynchronous connect, disconnect, and send_packet methods.
- Servers support asynchronous start_server, stop_server, send_packet, and close_connection methods.
- These provide a uniform interface across different transport implementations.

### TCP and UNIX Socket Transports

- TcpClient and TcpServer implement TCP transports based on asyncio streams.
- SocketClient and SocketServer implement UNIX domain socket transports similarly.
- Support connection management, safe concurrent sending via queues, and callback-based packet reception handling.

### gRPC Transports

- GrpcClient and GrpcServer use grpc.aio to implement asynchronous gRPC streaming transports.
- Support SSL/TLS configuration for secure connections.
- Use generated protobuf stubs for packet serialization.
- Maintain connection state with per-connection async queues and death signals.

### HTTP Transports

- HttpClient uses httpx.AsyncClient with a worker pool consuming an asyncio queue.
- HttpServer runs Hypercorn with FastAPI to handle RESTful streaming endpoints.
- Support SSL/TLS options and client session lifecycle management.

### SSL Options

- SSLClientOptions and SSLServerOptions are dataclasses encapsulating SSL parameters.
- Provide methods to create ssl.SSLContext instances configured with certs, keys, CA bundles, ciphers, TLS versions, and verification modes.
- Parse CLI argument namespaces to conveniently create options.

### Utilities

- Utilities to parse transport URIs and create appropriate client and server
  transport instances.
- Supports schemes tcp, grpc, http, and socket with sensible defaults.
- Handles address parsing including IPv6, IPv4, hostnames, and UNIX socket paths.
- Provides functions to create broker transports for workers and clients.

## Notes

- Transports use asyncio for concurrency and non-blocking IO.
- All transport implementations use callbacks to notify of incoming packets and connection events.
- The transport layer is protocol-independent beyond packet serialization,
  allowing ReasonChip to be run over multiple network protocols transparently.
- SSL context creation respects strict validation and version enforcement.
- HTTP server transports are powered by Hypercorn and FastAPI for performant async HTTP.
- gRPC implementations rely on generated protobuf stubs in `grpc_stubs/`.
- Logging is integrated for debug and error tracking across transports.

