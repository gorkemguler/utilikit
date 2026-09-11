"""Uniform error type + FastAPI handlers.

Every handled failure comes back as::

    { "error": { "type": "...", "message": "...", "detail": {...} } }
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ToolError(Exception):
    """Raise from any tool for a clean 4xx/5xx with a typed body."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        type: str = "tool_error",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.type = type
        self.detail = detail or {}


class UpstreamError(ToolError):
    def __init__(self, message: str, **kw: Any) -> None:
        kw.setdefault("status_code", 502)
        kw.setdefault("type", "upstream_error")
        super().__init__(message, **kw)


class FeatureUnavailable(ToolError):
    def __init__(self, message: str, **kw: Any) -> None:
        kw.setdefault("status_code", 503)
        kw.setdefault("type", "feature_unavailable")
        super().__init__(message, **kw)


def _body(type_: str, message: str, detail: dict | None = None) -> dict:
    return {"error": {"type": type_, "message": message, "detail": detail or {}}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ToolError)
    async def _tool_error(_: Request, exc: ToolError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_body(exc.type, exc.message, exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_body("validation_error", "Request parameters are invalid.", {"errors": _safe_errors(exc)}),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_body("http_error", str(exc.detail)),
            headers=exc.headers,
        )


def _safe_errors(exc: RequestValidationError) -> list:
    """errors() can contain non-JSON values (e.g. bytes ctx); coerce to str."""
    out = []
    for e in exc.errors():
        out.append(
            {k: (v if isinstance(v, (str, int, float, bool, type(None), list, dict)) else str(v)) for k, v in e.items()}
        )
    return out
