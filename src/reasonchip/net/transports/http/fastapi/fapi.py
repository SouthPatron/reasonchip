# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import time

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from ..common import CallbackHooks


# ****************************** GENERAL FUNCTIONS ************************


def setup_fapi(callbacks: CallbackHooks) -> FastAPI:

    # Create the FastAPI app
    app = FastAPI()

    # Callback hooks
    app.state.callback_hooks = callbacks

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ****************************** MIDDLEWARE *******************************

    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        """
        Record response time as response headera 'X-Process-Time'.
        """
        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000000
        response.headers["X-Process-Time"] = str(int(process_time))
        return response

    # ****************************** ENDPOINTS ********************************

    @app.get("/")
    async def root():
        return RedirectResponse(
            url="/docs",
            status_code=302,
        )

    from . import v1

    v1.populate(app)
    return app
