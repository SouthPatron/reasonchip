# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

"""
# OpenAI Chat Completion Chipset

This module provides functionality for interacting with OpenAI's chat completion API.
It defines request and response models, handles API interactions, and registers
a chip for generating chat completions.

## Features:
- Configurable OpenAI API client settings.
- Supports non-streaming chat completion requests.
- Handles various API errors gracefully.
"""

import typing
import logging
import openai

from openai.types.chat import ChatCompletion
from openai.types.chat.completion_create_params import (
    CompletionCreateParamsNonStreaming,
)

from pydantic import BaseModel, Field, HttpUrl

from reasonchip.core.engine.registry import Registry


class ClientSettings(BaseModel):
    """
    Configuration settings for OpenAI's API client.
    """

    api_key: typing.Optional[str] = Field(
        default=None, description="The OpenAI API key."
    )
    organization: typing.Optional[str] = Field(
        default=None, description="The OpenAI organization ID."
    )
    project: typing.Optional[str] = Field(
        default=None, description="The OpenAI project ID."
    )
    base_url: typing.Optional[HttpUrl] = Field(
        default=None, description="The base URL for the request."
    )
    websocket_base_url: typing.Optional[HttpUrl] = Field(
        default=None, description="The base URL for the websocket."
    )
    timeout: typing.Optional[float] = Field(
        default=60, description="The timeout for the request."
    )
    max_retries: typing.Optional[int] = Field(
        default=openai.DEFAULT_MAX_RETRIES,
        description="The maximum number of retries.",
    )
    default_headers: typing.Optional[typing.Dict[str, str]] = Field(
        default=None, description="The default headers for the request."
    )
    default_query: typing.Optional[typing.Dict[str, object]] = Field(
        default=None, description="The default query parameters."
    )


class ChatCompletionRequest(BaseModel):
    """
    Request structure for chat completion.
    """

    client_settings: ClientSettings = Field(
        description="Configuration for the OpenAI API client."
    )
    create_params: CompletionCreateParamsNonStreaming = Field(
        description="Parameters for the chat completion request."
    )


class ChatCompletionResponse(BaseModel):
    """
    Response structure for chat completion.
    """

    status: typing.Literal[
        "OK",
        "CONNECTION_ERROR",
        "RATE_LIMIT",
        "API_ERROR",
        "ERROR",
    ] = Field(description="Status of the request.")
    status_code: typing.Optional[int] = Field(
        default=None, description="The HTTP status code of the response."
    )
    completion: typing.Optional[ChatCompletion] = Field(
        default=None, description="The chat completion result (if successful)."
    )


@Registry.register
async def chat_completion(
    request: ChatCompletionRequest,
) -> ChatCompletionResponse:
    """
    Generates a chat completion using OpenAI's API.

    This is a pure wrapper around the OpenAI API, which handles the request
    and returns the response in a structured format. If you need to know
    what the API response looks like, refer to the OpenAI API documentation.

    [OpenAI API Reference](https://platform.openai.com/docs/api-reference/introduction)
    """

    try:
        # Create OpenAI client using provided settings
        client = openai.AsyncOpenAI(**request.client_settings.model_dump())

        # Convert request parameters to dictionary format
        params = dict(request.create_params)

        # Send the chat completion request to OpenAI
        completion = await client.chat.completions.create(**params)
        return ChatCompletionResponse(
            status="OK",
            completion=completion,
        )

    except openai.APIConnectionError as e:
        logging.exception(e)
        return ChatCompletionResponse(
            status="CONNECTION_ERROR",
            status_code=0,
        )

    except openai.RateLimitError as e:
        logging.exception(e)
        return ChatCompletionResponse(
            status="RATE_LIMIT",
            status_code=429,
        )

    except openai.APIStatusError as e:
        logging.exception(e)
        return ChatCompletionResponse(
            status="API_ERROR",
            status_code=e.status_code,
        )

    except Exception as e:
        logging.exception(e)
        return ChatCompletionResponse(
            status="ERROR",
        )
