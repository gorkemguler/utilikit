"""In-process token-bucket rate limiter (ASGI middleware).

Per identity (API key prefix, or client IP). Good enough for a single-process
self-hosted deployment; put a real limiter in front if you run several workers.
"""

from __future__ import annotations

import threading
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .config import get_settings
from .security import REQUESTS, TOOL_HITS, client_identity


class _Bucket:
    __slots__ = ("tokens", "updated")

    def __init__(self, tokens: float) -> None:
        self.tokens = tokens
        self.updated = time.monotonic()


class RateLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        s = get_settings()
        self.rate_per_sec = max(s.rate_limit_per_min, 1) / 60.0
        self.capacity = float(max(s.rate_limit_burst, 1))
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def _allow(self, identity: str) -> tuple[bool, float]:
        with self._lock:
            now = time.monotonic()
            b = self._buckets.get(identity)
            if b is None:
                b = self._buckets[identity] = _Bucket(self.capacity)
            b.tokens = min(self.capacity, b.tokens + (now - b.updated) * self.rate_per_sec)
            b.updated = now
            if b.tokens >= 1.0:
                b.tokens -= 1.0
                return True, b.tokens
            retry = (1.0 - b.tokens) / self.rate_per_sec
            return False, retry

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from starlette.requests import Request

        request = Request(scope, receive)
        path = scope["path"]
        exempt = path in {"/", "/healthz", "/metrics", "/favicon.ico"} or path.startswith("/static")

        if not exempt:
            ok, info = self._allow(client_identity(request))
            if not ok:
                await _send_429(send, retry_after=max(1, round(info)))
                REQUESTS["429"] += 1
                return

        seg = "/".join(path.split("/")[1:3])
        if seg:
            TOOL_HITS[seg] += 1

        async def _send(message: Message) -> None:
            if message["type"] == "http.response.start":
                REQUESTS[f"{message['status'] // 100}xx"] += 1
            await send(message)

        await self.app(scope, receive, _send)


async def _send_429(send: Send, retry_after: int) -> None:
    body = b'{"error":{"type":"rate_limited","message":"Too many requests. Slow down."}}'
    await send(
        {
            "type": "http.response.start",
            "status": 429,
            "headers": [
                (b"content-type", b"application/json"),
                (b"retry-after", str(retry_after).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
