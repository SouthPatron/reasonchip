# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

from .stream.stream import router as stream_router


def populate(app):
    app.include_router(stream_router, prefix="/v1/stream", tags=["Stream"])
