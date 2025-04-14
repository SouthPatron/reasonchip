# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

"""
# Telegram Sending Chipset

This module provides a flexible wrapper for sending messages via Telegram's Bot API.
It defines a dynamic chip that can execute any Telegram sending method asynchronously,
with configurable client settings and error handling.

## Features:
- Supports all Telegram Bot API sending methods (e.g., sendMessage, sendPhoto, sendVideo).
- Configurable Telegram bot token and chat settings.
- Dynamic method execution with flexible parameters.
- Handles connection errors, rate limits, and invalid methods gracefully.
"""

import typing
import logging

from telegram import Bot
from telegram.error import (
    TelegramError,
    NetworkError,
    TimedOut,
    InvalidToken,
)

from pydantic import BaseModel, Field

from reasonchip.core.engine.registry import Registry


class TelegramClientSettings(BaseModel):
    """
    Configuration settings for the Telegram async client.
    """

    bot_token: str = Field(
        description="The Telegram Bot API token obtained from BotFather.",
    )
    timeout: typing.Optional[float] = Field(
        default=60,
        description="Request timeout in seconds.",
    )


class TelegramSendRequest(BaseModel):
    """
    Request structure for sending a Telegram message.
    """

    client_settings: TelegramClientSettings = Field(
        description="Configuration for the Telegram Bot client."
    )
    chat_id: typing.Union[str, int] = Field(
        description="Unique identifier for the target chat or username of the target channel (e.g., '@channelusername').",
    )
    method: str = Field(
        description="The Telegram Bot API method to execute (e.g., 'sendMessage', 'sendPhoto', 'sendDocument').",
    )
    params: typing.Dict[str, typing.Any] = Field(
        default_factory=dict,
        description="Additional parameters for the method (e.g., 'text', 'photo', 'caption').",
    )


class TelegramSendResponse(BaseModel):
    """
    Response structure for Telegram sending operations.
    """

    status: typing.Literal[
        "OK",
        "CONNECTION_ERROR",
        "RATE_LIMIT",
        "INVALID_TOKEN",
        "METHOD_NOT_FOUND",
        "TELEGRAM_ERROR",
        "ERROR",
    ] = Field(description="Status of the request.")
    result: typing.Optional[typing.Any] = Field(
        default=None,
        description="The result of the Telegram operation (if successful).",
    )
    error_message: typing.Optional[str] = Field(
        default=None,
        description="Error message if the operation failed.",
    )


@Registry.register
async def telegram_send(request: TelegramSendRequest) -> TelegramSendResponse:
    """
    Sends a message or media using Telegram's Bot API.

    This chip dynamically executes any Telegram sending method (e.g.,
    sendMessage, sendPhoto) based on the provided method name and parameters.
    Refer to the Telegram Bot API documentation for available methods and
    parameters:

    [Telegram Bot API Reference](https://core.telegram.org/bots/api)
    """

    try:
        # Create Telegram Bot client
        bot = Bot(
            token=request.client_settings.bot_token,
        )

        await bot.initialize()

        # Ensure the method exists on the Bot client (case-insensitive matching)
        method_name = request.method.lower()
        available_methods = {
            name.lower(): name
            for name in dir(bot)
            if callable(getattr(bot, name))
        }
        if method_name not in available_methods:
            return TelegramSendResponse(
                status="METHOD_NOT_FOUND",
                error_message=f"Method '{request.method}' not found on Telegram Bot client.",
            )

        # Add chat_id to params if not already present
        params = request.params.copy()
        if "chat_id" not in params:
            params["chat_id"] = request.chat_id

        # Get the actual method name (preserving original casing) and execute it
        method = getattr(bot, available_methods[method_name])
        result = await method(**params)

        return TelegramSendResponse(
            status="OK",
            result=result,
        )

    except TimedOut as e:
        logging.exception(e)
        return TelegramSendResponse(
            status="RATE_LIMIT",
            error_message="Request timed out, possibly due to rate limiting.",
        )

    except NetworkError as e:
        logging.exception(e)
        return TelegramSendResponse(
            status="CONNECTION_ERROR",
            error_message=str(e),
        )

    except InvalidToken as e:
        logging.exception(e)
        return TelegramSendResponse(
            status="INVALID_TOKEN",
            error_message=str(e),
        )

    except TelegramError as e:
        logging.exception(e)
        return TelegramSendResponse(
            status="TELEGRAM_ERROR",
            error_message=str(e),
        )

    except Exception as e:
        logging.exception(e)
        return TelegramSendResponse(
            status="ERROR",
            error_message=f"Unexpected error: {str(e)}",
        )
