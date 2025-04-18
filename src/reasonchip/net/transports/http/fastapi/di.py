# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

from fastapi import Request

from ..common import CallbackHooks


# ************* Dependency injections ****************************************


# Get the callbacks
def get_callbacks(request: Request) -> CallbackHooks:
    hooks: CallbackHooks = request.app.state.callback_hooks
    return hooks
