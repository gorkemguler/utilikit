"""API-key auth (header ``X-API-Key`` or ``?api_key=``) + tiny in-process metrics."""

from __future__ import annotations

import secrets
from collections import Counter

from fastapi import Request

from .config import get_settings
from .errors import ToolError

# Scraped by GET /metrics (Prometheus text format).
REQUESTS: Counter = Counter()  # status class -> count, e.g. "2xx"
TOOL_HITS: Counter = Counter()  # first two path segments -> count


def client_identity(request: Request) -> str:
    key = request.headers.get("x-api-key") or request.query_params.get("api_key")
    if key:
        return f"key:{key[:8]}"
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    return f"ip:{ip}"


async def require_key(request: Request) -> None:
    """Dependency mounted on the ``/v1`` routers. No-op when no keys are configured."""
    settings = get_settings()
    if not settings.keys:
        return
    supplied = request.headers.get("x-api-key") or request.query_params.get("api_key") or ""
    if not any(secrets.compare_digest(supplied, k) for k in settings.keys):
        raise ToolError(
            "Missing or invalid API key (send the X-API-Key header).",
            status_code=401,
            type="unauthorized",
        )
