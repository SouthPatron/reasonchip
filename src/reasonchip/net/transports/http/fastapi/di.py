# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import logging
from fastapi import Request

from ..common import CallbackHooks

log = logging.getLogger(__name__)


# ************* Dependency injections ****************************************


# Get the callbacks
def get_callbacks(request: Request) -> CallbackHooks:
    """
    Retrieve callback hooks from the FastAPI app state.

    :param request: The incoming FastAPI request.

    :return: The CallbackHooks instance stored in the app state.
    """
    hooks: CallbackHooks = request.app.state.callback_hooks
    log.debug("Retrieved callback hooks from app state")
    return hooks
