"""SSRF-guarded outbound HTTP.

Any tool that fetches a user-supplied URL (unfurl, readability, http headers,
screenshot target validation, …) goes through here. It:

* allows only ``http`` / ``https``;
* resolves the hostname and refuses private / loopback / link-local / reserved
  / cloud-metadata addresses (unless ``UTILIKIT_ALLOW_PRIVATE_FETCH=true``);
* re-checks every redirect hop;
* caps redirects, body size and total time.

It is *defence in depth*, not a licence to expose the API unauthenticated.
"""

from __future__ import annotations

import ipaddress
import socket
import time
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import httpx

from .config import Settings, get_settings
from .errors import ToolError, UpstreamError

_BLOCKED_HOST_SUFFIXES = (".local", ".internal", ".localdomain", ".lan")
_BLOCKED_HOST_EXACT = {"localhost", "metadata.google.internal", "metadata", "instance-data"}


class BlockedTarget(ToolError):
    def __init__(self, message: str, detail: dict | None = None) -> None:
        super().__init__(message, status_code=400, type="blocked_target", detail=detail or {})


@dataclass(slots=True)
class FetchResult:
    url: str
    status_code: int
    headers: dict[str, str]
    content: bytes
    text: str
    elapsed_ms: int
    history: list[str] = field(default_factory=list)
    truncated: bool = False

    @property
    def content_type(self) -> str:
        return self.headers.get("content-type", "").split(";")[0].strip().lower()


def _ip_is_public(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return not (
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified
    )


def _suffix_match(host: str, patterns: list[str]) -> bool:
    host = host.lower().rstrip(".")
    return any(host == p or host.endswith("." + p.lstrip(".")) for p in patterns if p)


def assert_host_allowed(host: str, settings: Settings | None = None) -> list[str]:
    """Resolve ``host`` and raise :class:`BlockedTarget` unless every address is OK.

    Returns the resolved IP strings.
    """
    settings = settings or get_settings()
    host = host.strip().lower().rstrip(".")
    if not host:
        raise BlockedTarget("Empty host.")

    if settings.fetch_allow_hosts:
        allow = [h.strip() for h in settings.fetch_allow_hosts.split(",") if h.strip()]
        if not _suffix_match(host, allow):
            raise BlockedTarget(f"Host {host!r} is not in UTILIKIT_FETCH_ALLOW_HOSTS.")

    deny = list(_BLOCKED_HOST_SUFFIXES)
    if settings.fetch_deny_hosts:
        deny += [h.strip() for h in settings.fetch_deny_hosts.split(",") if h.strip()]
    if host in _BLOCKED_HOST_EXACT or _suffix_match(host, deny):
        raise BlockedTarget(f"Host {host!r} is blocked.")

    # A literal IP in the URL still has to pass the address check.
    try:
        literal = ipaddress.ip_address(host)
        addrs = [str(literal)]
    except ValueError:
        try:
            infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
        except OSError as exc:
            raise BlockedTarget(f"Cannot resolve {host!r}: {exc}") from exc
        addrs = sorted({i[4][0] for i in infos})

    if not settings.allow_private_fetch:
        for a in addrs:
            ip = ipaddress.ip_address(a.split("%")[0])
            if not _ip_is_public(ip):
                raise BlockedTarget(
                    f"{host!r} resolves to non-public address {a}.",
                    detail={"resolved": addrs},
                )
    return addrs


def _check_url(raw: str, settings: Settings) -> tuple[str, str]:
    parts = urlsplit(raw.strip())
    if parts.scheme not in {"http", "https"}:
        raise BlockedTarget(f"Only http/https URLs are allowed (got {parts.scheme!r}).")
    if not parts.hostname:
        raise BlockedTarget("URL has no host.")
    assert_host_allowed(parts.hostname, settings)
    return raw, parts.hostname


async def fetch(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    max_bytes: int | None = None,
    allow_redirects: bool = True,
    settings: Settings | None = None,
) -> FetchResult:
    settings = settings or get_settings()
    max_bytes = max_bytes or settings.fetch_max_bytes
    hdrs = {"user-agent": settings.fetch_user_agent, "accept": "*/*"}
    if headers:
        hdrs.update({k.lower(): v for k, v in headers.items()})

    history: list[str] = []
    current = url
    started = time.monotonic()

    async with httpx.AsyncClient(
        follow_redirects=False,
        timeout=settings.fetch_timeout_seconds,
        headers=hdrs,
    ) as client:
        for _hop in range(settings.fetch_max_redirects + 1):
            _check_url(current, settings)
            try:
                async with client.stream(method, current) as resp:
                    if allow_redirects and resp.is_redirect and resp.headers.get("location"):
                        history.append(current)
                        current = str(resp.url.join(resp.headers["location"]))
                        continue

                    chunks: list[bytes] = []
                    size = 0
                    truncated = False
                    async for chunk in resp.aiter_bytes():
                        size += len(chunk)
                        if size > max_bytes:
                            chunks.append(chunk[: max_bytes - (size - len(chunk))])
                            truncated = True
                            break
                        chunks.append(chunk)
                    body = b"".join(chunks)
                    try:
                        text = body.decode(resp.encoding or "utf-8", errors="replace")
                    except (LookupError, ValueError):
                        text = body.decode("utf-8", errors="replace")
                    return FetchResult(
                        url=str(resp.url),
                        status_code=resp.status_code,
                        headers={k.lower(): v for k, v in resp.headers.items()},
                        content=body,
                        text=text,
                        elapsed_ms=int((time.monotonic() - started) * 1000),
                        history=history,
                        truncated=truncated,
                    )
            except httpx.HTTPError as exc:
                raise UpstreamError(f"Request to {current} failed: {exc}") from exc

    raise UpstreamError(f"Too many redirects (> {settings.fetch_max_redirects}).")
