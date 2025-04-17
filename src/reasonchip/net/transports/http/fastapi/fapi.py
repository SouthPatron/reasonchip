# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import time
import logging

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from ..common import CallbackHooks

log = logging.getLogger(__name__)


# ****************************** GENERAL FUNCTIONS ************************


def setup_fapi(callbacks: CallbackHooks) -> FastAPI:
    """
    Setup and configure the FastAPI application.

    :param callbacks: Callback hooks to attach to the app state.
    :return: Configured FastAPI application.
    """

    # Create the FastAPI app
    app = FastAPI()
    log.info("FastAPI app instance created.")

    # Callback hooks
    app.state.callback_hooks = callbacks
    log.info("Callback hooks assigned to app state.")

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    log.info("CORS middleware added with empty allow_origins.")

    # ****************************** MIDDLEWARE *******************************

    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        """
        Record response time as response header 'X-Process-Time'.

        :param request: The incoming request.
        :param call_next: The next handler in the middleware chain.
        :return: Response with process time header added.
        """
        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000000
        response.headers["X-Process-Time"] = str(int(process_time))
        log.info(
            f"Processed request {request.url.path} in {int(process_time)} microseconds."
        )
        return response

    # ****************************** ENDPOINTS ********************************

    @app.get("/")
    async def root():
        """
        Redirect root URL to /docs.

        :return: RedirectResponse with status code 302.
        """
        log.info("Root endpoint called, redirecting to /docs.")
        return RedirectResponse(
            url="/docs",
            status_code=302,
        )

    from . import v1

    v1.populate(app)
    log.info("Version 1 API populated.")
    return app
