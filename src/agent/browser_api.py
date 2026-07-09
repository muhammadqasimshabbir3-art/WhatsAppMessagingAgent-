"""Lightweight HTTP API for embedded WhatsApp browser setup in the web UI."""

from __future__ import annotations

import os

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route

from agent.browser_service import (
    get_account_info,
    get_browser_status,
    setup_browser,
)


async def account_info(_request):
    return JSONResponse(get_account_info())


async def browser_status(_request):
    return JSONResponse(await run_in_threadpool(get_browser_status))


async def browser_setup(_request):
    try:
        status = await run_in_threadpool(setup_browser)
        return JSONResponse(status)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


routes = [
    Route("/account", account_info, methods=["GET"]),
    Route("/browser/status", browser_status, methods=["GET"]),
    Route("/browser/setup", browser_setup, methods=["POST"]),
]

app = Starlette(routes=routes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def main() -> None:
    import uvicorn

    port = int(os.getenv("BROWSER_API_PORT", "2025"))
    uvicorn.run("agent.browser_api:app", host="127.0.0.1", port=port, reload=False)


if __name__ == "__main__":
    main()
