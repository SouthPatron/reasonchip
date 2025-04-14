# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

"""
# Redis Command Chipset

This module provides a flexible wrapper for executing Redis commands using
redis-py. It defines a dynamic chip that can execute any Redis method
asynchronously, with configurable client settings and error handling.

## Features:
- Configurable Redis client settings (host, port, database, etc.).
- Dynamic method execution based on provided method name and parameters.
- Supports asynchronous Redis operations.
- Handles connection errors and invalid method names gracefully.
"""

import typing

from redis.asyncio import Redis, ConnectionPool, RedisError
from pydantic import BaseModel, Field

from reasonchip.core.engine.registry import Registry


class RedisClientSettings(BaseModel):
    """
    Configuration settings for the Redis async client.
    """

    host: str = Field(
        default="localhost", description="The Redis server hostname."
    )
    port: int = Field(default=6379, description="The Redis server port.")
    db: int = Field(default=0, description="The Redis database number.")
    username: typing.Optional[str] = Field(
        default=None, description="The username for authentication."
    )
    password: typing.Optional[str] = Field(
        default=None, description="The password for authentication."
    )
    ssl: bool = Field(
        default=False, description="Whether to use SSL for the connection."
    )
    timeout: typing.Optional[float] = Field(
        default=60, description="Socket timeout in seconds."
    )
    max_connections: typing.Optional[int] = Field(
        default=None, description="Maximum number of connections in the pool."
    )


class RedisExecuteRequest(BaseModel):
    """
    Request structure for executing a Redis command.
    """

    client_settings: RedisClientSettings = Field(
        default_factory=RedisClientSettings,
        description="Configuration for the Redis async client.",
    )
    method: str = Field(
        description="The Redis method to execute (e.g., 'set', 'get', 'hset').",
    )
    args: typing.List[typing.Any] = Field(
        default_factory=list,
        description="Positional arguments for the method.",
    )
    kwargs: typing.Dict[str, typing.Any] = Field(
        default_factory=dict,
        description="Keyword arguments for the method.",
    )


class RedisExecuteResponse(BaseModel):
    """
    Response structure for Redis command execution.
    """

    status: typing.Literal[
        "OK",
        "CONNECTION_ERROR",
        "TIMEOUT",
        "METHOD_NOT_FOUND",
        "REDIS_ERROR",
        "ERROR",
    ] = Field(description="Status of the request.")

    result: typing.Optional[typing.Any] = Field(
        default=None,
        description="The result of the Redis command (if successful).",
    )
    error_message: typing.Optional[str] = Field(
        default=None, description="Error message if the command failed."
    )


@Registry.register
async def redis_execute(request: RedisExecuteRequest) -> RedisExecuteResponse:
    """
    Executes a Redis command dynamically using redis-py’s async client.

    This chip allows you to execute any Redis command by specifying the method name
    and its parameters. It validates the method exists on the Redis client before
    execution and handles errors appropriately.

    Refer to redis-py documentation for available commands:
    [redis-py Reference](https://redis-py.readthedocs.io/en/stable/)
    """

    client = None

    try:
        # Create a connection pool and Redis client
        pool = ConnectionPool.from_url(
            f"redis://{request.client_settings.host}:{request.client_settings.port}/{request.client_settings.db}",
            username=request.client_settings.username,
            password=request.client_settings.password,
            socket_timeout=request.client_settings.timeout,
            max_connections=request.client_settings.max_connections,
        )
        client = Redis(connection_pool=pool)

        # Check if the method exists on the client
        if not hasattr(client, request.method):
            return RedisExecuteResponse(
                status="METHOD_NOT_FOUND",
                error_message=f"Method '{request.method}' not found on Redis client.",
            )

        # Get the method and execute it dynamically
        method = getattr(client, request.method)
        result = await method(*request.args, **request.kwargs)

        return RedisExecuteResponse(
            status="OK",
            result=result,
        )

    except ConnectionError as e:
        return RedisExecuteResponse(
            status="CONNECTION_ERROR",
            error_message=str(e),
        )

    except TimeoutError as e:
        return RedisExecuteResponse(
            status="TIMEOUT",
            error_message=str(e),
        )

    except RedisError as e:
        return RedisExecuteResponse(
            status="REDIS_ERROR",
            error_message=str(e),
        )

    except Exception as e:
        return RedisExecuteResponse(
            status="ERROR",
            error_message=str(e),
        )

    finally:
        if client:
            await client.aclose()
