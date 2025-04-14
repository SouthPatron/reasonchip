# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

"""
# HTTP Requests Chipset

This module provides an HTTP request chipset for ReasonChip. It enables
asynchronous HTTP requests using `httpx.AsyncClient` and returns
structured responses.

This chipset is a wrapper around httpx. You can find httpx documentation
here: [HTTPX Documentation](https://www.python-httpx.org/)

## Features
- Supports standard HTTP methods (`GET`, `POST`, `PUT`, `DELETE`, etc.).
- Handles request timeouts, network errors, and various HTTP errors gracefully.
- Returns structured response data with status, headers, and content.
- Limits response content size to prevent excessive memory usage.


"""

import typing
import json
import httpx

from pydantic import BaseModel, Field, HttpUrl

from reasonchip.core.engine.registry import Registry


class HttpRequestRequest(BaseModel):
    """
    Model representing an HTTP request.
    """

    method: typing.Literal[
        "GET", "OPTIONS", "HEAD", "POST", "PUT", "DELETE", "PATCH"
    ] = Field(
        ...,
        description="HTTP method to use for the request (e.g., GET, POST, DELETE).",
    )
    url: HttpUrl = Field(..., description="Target URL for the request.")
    timeout: float = Field(
        default=60,
        description="Request timeout in seconds.",
    )
    headers: typing.Dict[str, str] = Field(
        default_factory=dict,
        description="Optional HTTP headers to include in the request.",
    )
    content: typing.Optional[bytes] = Field(
        default=None,
        description="Optional request body content as bytes.",
    )


class HttpRequestResponse(BaseModel):
    """
    Model representing the response from an HTTP request.
    """

    status: typing.Literal[
        "OK",
        "TIMEOUT_ERROR",
        "NETWORK_ERROR",
        "PROTOCOL_ERROR",
        "PROXY_ERROR",
        "UNSUPPORTED_PROTOCOL_ERROR",
        "DECODING_ERROR",
        "TOO_MANY_REDIRECTS",
        "HTTP_STATUS_ERROR",
        "INVALID_URL",
        "COOKIE_CONFLICT",
        "STREAM_ERROR",
        "ERROR",
    ] = Field(..., description="Status of the HTTP request execution.")

    status_code: typing.Optional[int] = Field(
        default=None, description="HTTP response status code (e.g., 200, 404)."
    )
    headers: typing.Dict[str, str] = Field(
        default_factory=dict,
        description="Response headers received from the server.",
    )
    content: typing.Optional[bytes] = Field(
        default=None,
        description="Response body content as bytes.",
    )


@Registry.register
async def http_request(req: HttpRequestRequest) -> HttpRequestResponse:
    """
    Executes an HTTP request asynchronously using `httpx.AsyncClient` and
    returns the response.
    """
    MAX_CONTENT_LENGTH = 16 * (
        1024 * 1024
    )  # Maximum allowed response content size (16MB)

    async with httpx.AsyncClient() as client:
        try:
            async with client.stream(
                method=req.method,
                url=str(req.url),
                timeout=req.timeout,
                headers=req.headers,
                follow_redirects=True,
                content=req.content,
            ) as resp:
                resp.raise_for_status()

                content = b""
                content_size = 0
                async for chunk in resp.aiter_bytes():
                    content_size += len(chunk)
                    if content_size > MAX_CONTENT_LENGTH:
                        break

                    content += chunk

                headers = resp.headers.items()

                return HttpRequestResponse(
                    status="OK",
                    status_code=resp.status_code,
                    headers=dict(headers),
                    content=content,
                )

        except httpx.HTTPStatusError as e:
            return HttpRequestResponse(
                status="HTTP_STATUS_ERROR",
                status_code=e.response.status_code,
            )

        except httpx.TimeoutException:
            return HttpRequestResponse(status="TIMEOUT_ERROR")

        except httpx.NetworkError:
            return HttpRequestResponse(status="NETWORK_ERROR")

        except httpx.ProtocolError:
            return HttpRequestResponse(status="PROTOCOL_ERROR")

        except httpx.ProxyError:
            return HttpRequestResponse(status="PROXY_ERROR")

        except httpx.UnsupportedProtocol:
            return HttpRequestResponse(status="UNSUPPORTED_PROTOCOL_ERROR")

        except httpx.DecodingError:
            return HttpRequestResponse(status="DECODING_ERROR")

        except httpx.TooManyRedirects:
            return HttpRequestResponse(status="TOO_MANY_REDIRECTS")

        except httpx.InvalidURL:
            return HttpRequestResponse(status="INVALID_URL")

        except httpx.CookieConflict:
            return HttpRequestResponse(status="COOKIE_CONFLICT")

        except httpx.StreamError:
            return HttpRequestResponse(status="STREAM_ERROR")

        except Exception:
            return HttpRequestResponse(status="ERROR")


class PostJsonObjectRequest(BaseModel):
    """
    Model representing an HTTP request.
    """

    url: HttpUrl = Field(
        ...,
        description="Target URL for the request.",
    )
    timeout: float = Field(
        default=60,
        description="Request timeout in seconds.",
    )
    headers: typing.Dict[str, str] = Field(
        default_factory=dict,
        description="Optional HTTP headers to include in the request.",
    )
    content: typing.Optional[typing.Dict[str, typing.Any]] = Field(
        default_factory=dict,
        description="Optional request body content as bytes.",
    )


class PostJsonObjectResponse(BaseModel):
    """
    Model representing the response from an HTTP request.
    """

    status: typing.Literal[
        "OK",
        "TIMEOUT_ERROR",
        "NETWORK_ERROR",
        "PROTOCOL_ERROR",
        "PROXY_ERROR",
        "UNSUPPORTED_PROTOCOL_ERROR",
        "DECODING_ERROR",
        "TOO_MANY_REDIRECTS",
        "HTTP_STATUS_ERROR",
        "INVALID_URL",
        "COOKIE_CONFLICT",
        "STREAM_ERROR",
        "ERROR",
    ] = Field(
        ...,
        description="Status of the HTTP request execution.",
    )

    status_code: typing.Optional[int] = Field(
        default=None, description="HTTP response status code (e.g., 200, 404)."
    )
    headers: typing.Dict[str, str] = Field(
        default_factory=dict,
        description="Response headers received from the server.",
    )
    content: typing.Optional[bytes] = Field(
        default=None,
        description="Response body content as bytes.",
    )


@Registry.register
async def post_json_object(
    req: PostJsonObjectRequest,
) -> PostJsonObjectResponse:
    """
    Executes an HTTP request asynchronously using `httpx.AsyncClient` and
    returns the response. The request body is a JSON object.
    """
    MAX_CONTENT_LENGTH = 16 * (
        1024 * 1024
    )  # Maximum allowed response content size (16MB)

    async with httpx.AsyncClient() as client:
        try:
            content = json.dumps(req.content).encode("utf-8")

            headers = req.headers.copy()
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"

            async with client.stream(
                method="POST",
                url=str(req.url),
                timeout=req.timeout,
                headers=headers,
                follow_redirects=True,
                content=content,
            ) as resp:
                resp.raise_for_status()

                content = b""
                content_size = 0
                async for chunk in resp.aiter_bytes():
                    content_size += len(chunk)
                    if content_size > MAX_CONTENT_LENGTH:
                        break

                    content += chunk

                headers = resp.headers.items()

                return PostJsonObjectResponse(
                    status="OK",
                    status_code=resp.status_code,
                    headers=dict(headers),
                    content=content,
                )

        except httpx.HTTPStatusError as e:
            return PostJsonObjectResponse(
                status="HTTP_STATUS_ERROR",
                status_code=e.response.status_code,
            )

        except httpx.TimeoutException:
            return PostJsonObjectResponse(status="TIMEOUT_ERROR")

        except httpx.NetworkError:
            return PostJsonObjectResponse(status="NETWORK_ERROR")

        except httpx.ProtocolError:
            return PostJsonObjectResponse(status="PROTOCOL_ERROR")

        except httpx.ProxyError:
            return PostJsonObjectResponse(status="PROXY_ERROR")

        except httpx.UnsupportedProtocol:
            return PostJsonObjectResponse(status="UNSUPPORTED_PROTOCOL_ERROR")

        except httpx.DecodingError:
            return PostJsonObjectResponse(status="DECODING_ERROR")

        except httpx.TooManyRedirects:
            return PostJsonObjectResponse(status="TOO_MANY_REDIRECTS")

        except httpx.InvalidURL:
            return PostJsonObjectResponse(status="INVALID_URL")

        except httpx.CookieConflict:
            return PostJsonObjectResponse(status="COOKIE_CONFLICT")

        except httpx.StreamError:
            return PostJsonObjectResponse(status="STREAM_ERROR")

        except Exception:
            return PostJsonObjectResponse(status="ERROR")
