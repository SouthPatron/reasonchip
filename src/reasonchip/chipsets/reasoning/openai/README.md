# OpenAI Chat Completion Chipset

## Overview

This directory contains the reasoning chipset implementation for "OpenAI", specifically
providing a wrapper integration around OpenAI's Chat Completion API. It supports
non-streaming chat completion requests, managing client configuration, API calls,
and response handling.

## Filesystem Overview

| Location                        | Description                                     |
|-------------------------------|------------------------------------------------|
| [chat.py](./chat.py)           | Implements the OpenAI chat completion chip,   |
|                               | including API client configuration, request,  |
|                               | response models, and async call logic.         |

## Onboarding Approach

To understand the OpenAI chat completion chipset:

1. Familiarize yourself with the OpenAI Chat Completion API, including request
   parameters and response structure. Documentation is at
   https://platform.openai.com/docs/api-reference/introduction.

2. Review `chat.py` which contains a few key components:
   - `ClientSettings`: a Pydantic model encapsulating API client configuration such
     as API keys, organization, base URLs, and timeout settings.

   - `ChatCompletionRequest`: composes client settings and non-streaming chat
     completion parameters into a single request model.

   - `ChatCompletionResponse`: returns a typed response containing status, HTTP
     status code, and optionally the OpenAI chat completion result.

   - `chat_completion` async function registered as a chipset component to
     execute the chat completion request, handle exceptions from the OpenAI
     client, and wrap responses.

3. Understand the error handling semantics that categorize errors into connection
   errors, rate limits, API errors, or generic errors.

4. Note that the code uses Pydantic for data validation and the openai python SDK
   for asynchronous API calls.

## Design Notes

- The async `chat_completion` function acts as a direct adaptor between ReasonChip
  and OpenAI's chat API.

- Use of `openai.AsyncOpenAI` with injected client settings allows flexible API endpoint
  and retry configuration.

- The design cleanly separates configuration, request formatting, and error handling
  from the actual API call.

- Responses include a strongly typed status to allow downstream components
to react appropriately.

## Dependencies

- [OpenAI Python SDK](https://pypi.org/project/openai/) for async Chat Completion.
- Pydantic for data model validation.
- ReasonChip's `Registry` interface to register chipset components.

This setup ensures extensibility and maintainability in managing OpenAI interactions
in the chipsets reasoning architecture.
