import typing
import logging
import openai

# Setup logging
log = logging.getLogger("reasonchip.chips.reasoning.openai")

from openai.types.responses import ParsedResponse
from openai.types.responses.response_create_params import (
    ResponseCreateParamsNonStreaming,
)

from pydantic import BaseModel, Field, HttpUrl


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


# This defines a ResponseCreateParamsNonStreaming as CreateParams
CreateParams = typing.Dict[str, typing.Any]


class ResponseRequest(BaseModel):
    """
    Request structure for chat completion.
    """

    client_settings: ClientSettings = Field(
        description="Configuration for the OpenAI API client."
    )
    create_params: CreateParams = Field(
        description="Parameters for the request."
    )


class ResponseResponse(BaseModel):
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
    completion: typing.Optional[ParsedResponse] = Field(
        default=None, description="The parsed response (if successful)."
    )


async def responses(request: ResponseRequest) -> ResponseResponse:
    """
    Generates a request using OpenAI's API.

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
        completion = await client.responses.parse(**params)
        return ResponseResponse(
            status="OK",
            completion=completion,
        )

    except openai.APIConnectionError as e:
        logging.exception(e)
        return ResponseResponse(
            status="CONNECTION_ERROR",
            status_code=0,
        )

    except openai.RateLimitError as e:
        logging.exception(e)
        return ResponseResponse(
            status="RATE_LIMIT",
            status_code=429,
        )

    except openai.APIStatusError as e:
        logging.exception(e)
        return ResponseResponse(
            status="API_ERROR",
            status_code=e.status_code,
        )

    except Exception as e:
        logging.exception(e)
        return ResponseResponse(
            status="ERROR",
        )


# ---- SIMPLE FUNCTIONS ------------------------------------------------------

T = typing.TypeVar("T")

# ----------------- LOGIC ----------------------------------------------------


async def json_reason(
    client_settings: ClientSettings,
    model: str,
    prompt: str,
    response: typing.Type[T],
) -> typing.Optional[T]:

    rc = await responses(
        ResponseRequest(
            client_settings=client_settings,
            create_params={
                "model": model,
                "instructions": "Please respond in JSON.",
                "input": prompt,
                "text_format": response,
            },
        )
    )

    if rc.status != "OK":
        log.error(f"Failed to reason: {rc}")
        return None

    assert rc.completion
    return rc.completion.output_parsed
