"""HTTP inspection + TLS certificate + TCP reachability tools."""

from __future__ import annotations

import asyncio
import socket
import ssl
import time
from datetime import UTC, datetime
from urllib.parse import urlsplit

from fastapi import APIRouter, Query

from ..cache import cached
from ..config import get_settings
from ..errors import ToolError, UpstreamError
from ..registry import Endpoint, ToolInfo, register
from ..safefetch import assert_host_allowed, fetch

router = APIRouter(prefix="/v1", tags=["http"])

_SECURITY_HEADERS = [
    "strict-transport-security",
    "content-security-policy",
    "x-content-type-options",
    "x-frame-options",
    "referrer-policy",
    "permissions-policy",
]


@router.get("/http/headers", summary="Fetch a URL and report status, headers, timing and size")
async def http_headers(
    url: str,
    method: str = Query("GET", pattern="^(GET|HEAD)$"),
) -> dict:
    res = await fetch(url, method=method, allow_redirects=True)
    present = {h: res.headers[h] for h in _SECURITY_HEADERS if h in res.headers}
    return {
        "final_url": res.url,
        "status_code": res.status_code,
        "elapsed_ms": res.elapsed_ms,
        "redirects": res.history,
        "content_type": res.content_type,
        "content_length": len(res.content),
        "truncated": res.truncated,
        "server": res.headers.get("server", ""),
        "headers": res.headers,
        "security_headers": {
            "present": present,
            "missing": [h for h in _SECURITY_HEADERS if h not in res.headers],
        },
    }


@router.get("/http/redirects", summary="Trace a URL's redirect chain")
async def http_redirects(url: str) -> dict:
    settings = get_settings()
    chain = []
    current = url
    import httpx

    async with httpx.AsyncClient(
        follow_redirects=False,
        timeout=settings.fetch_timeout_seconds,
        headers={"user-agent": settings.fetch_user_agent},
    ) as client:
        for _ in range(settings.fetch_max_redirects + 1):
            parts = urlsplit(current)
            if parts.scheme not in {"http", "https"} or not parts.hostname:
                raise ToolError(f"Bad URL in chain: {current}")
            assert_host_allowed(parts.hostname, settings)
            try:
                r = await client.request("GET", current)
            except httpx.HTTPError as exc:
                raise UpstreamError(f"{current} failed: {exc}") from exc
            hop = {"url": current, "status": r.status_code}
            if r.is_redirect and r.headers.get("location"):
                hop["location"] = str(r.url.join(r.headers["location"]))
                chain.append(hop)
                current = hop["location"]
                continue
            hop["final"] = True
            chain.append(hop)
            break
    return {"start": url, "hops": len(chain), "chain": chain, "final_url": chain[-1]["url"]}


@cached(ttl=600)
def _tls_cert(host: str, port: int) -> dict:
    from cryptography import x509
    from cryptography.hazmat.primitives.asymmetric import ec, rsa

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with (
            socket.create_connection((host, port), timeout=10) as sock,
            ctx.wrap_socket(sock, server_hostname=host) as ssock,
        ):
            der = ssock.getpeercert(binary_form=True)
            proto = ssock.version()
    except (OSError, ssl.SSLError) as exc:
        raise UpstreamError(f"TLS handshake with {host}:{port} failed: {exc}") from exc

    cert = x509.load_der_x509_certificate(der)
    try:
        sans = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(
            x509.DNSName
        )
    except x509.ExtensionNotFound:
        sans = []
    key = cert.public_key()
    if isinstance(key, rsa.RSAPublicKey):
        key_desc = f"RSA {key.key_size}"
    elif isinstance(key, ec.EllipticCurvePublicKey):
        key_desc = f"EC {key.curve.name}"
    else:
        key_desc = type(key).__name__
    not_after = cert.not_valid_after_utc
    not_before = cert.not_valid_before_utc
    now = datetime.now(UTC)
    return {
        "host": host,
        "port": port,
        "tls_version": proto,
        "subject": cert.subject.rfc4514_string(),
        "issuer": cert.issuer.rfc4514_string(),
        "serial": format(cert.serial_number, "x"),
        "not_before": not_before.isoformat(),
        "not_after": not_after.isoformat(),
        "days_until_expiry": (not_after - now).days,
        "expired": now > not_after,
        "not_yet_valid": now < not_before,
        "self_signed": cert.subject == cert.issuer,
        "signature_algorithm": cert.signature_hash_algorithm.name if cert.signature_hash_algorithm else "?",
        "public_key": key_desc,
        "subject_alt_names": sans,
    }


@router.get("/tls/cert", summary="Inspect the TLS certificate served by a host")
def tls_cert(host: str, port: int = Query(443, ge=1, le=65535)) -> dict:
    host = host.strip().replace("https://", "").replace("http://", "").split("/")[0]
    assert_host_allowed(host)
    return _tls_cert(host, port)


async def _one_connect(host: str, port: int, timeout: float) -> float | None:
    loop = asyncio.get_running_loop()
    start = time.monotonic()
    try:
        fut = loop.create_connection(asyncio.Protocol, host, port)
        transport, _ = await asyncio.wait_for(fut, timeout)
        transport.close()
        return (time.monotonic() - start) * 1000
    except (TimeoutError, OSError):
        return None


@router.get("/net/tcp-ping", summary="Measure TCP connect latency to host:port (not ICMP)")
async def tcp_ping(
    host: str,
    port: int = Query(443, ge=1, le=65535),
    count: int = Query(4, ge=1, le=10),
    timeout: float = Query(3.0, ge=0.2, le=10.0),
) -> dict:
    host = host.strip().split("/")[0]
    assert_host_allowed(host)
    times: list[float] = []
    for _ in range(count):
        ms = await _one_connect(host, port, timeout)
        if ms is not None:
            times.append(round(ms, 2))
    return {
        "host": host,
        "port": port,
        "sent": count,
        "received": len(times),
        "loss_pct": round((count - len(times)) / count * 100, 1),
        "rtt_ms": {
            "min": min(times) if times else None,
            "avg": round(sum(times) / len(times), 2) if times else None,
            "max": max(times) if times else None,
        },
        "samples": times,
    }


@router.get("/net/port-check", summary="Check whether one or more TCP ports are open")
async def port_check(
    host: str,
    ports: str = Query("80,443", description="Comma-separated port list"),
    timeout: float = Query(3.0, ge=0.2, le=10.0),
) -> dict:
    host = host.strip().split("/")[0]
    assert_host_allowed(host)
    want: list[int] = []
    for p in ports.split(","):
        p = p.strip()
        if p.isdigit() and 1 <= int(p) <= 65535:
            want.append(int(p))
    if not want:
        raise ToolError("Give at least one valid port.")
    results = {}
    for port in want[:32]:
        ms = await _one_connect(host, port, timeout)
        results[str(port)] = {"open": ms is not None, "latency_ms": round(ms, 2) if ms else None}
    return {"host": host, "results": results}


register(
    ToolInfo(
        key="net_http",
        title="HTTP & TLS inspection",
        category="Network & OSINT",
        description=(
            "Headers + security-header audit, redirect-chain trace, TLS certificate "
            "inspector, TCP ping and port check. All SSRF-guarded."
        ),
        router=router,
        endpoints=[
            Endpoint("GET", "/v1/http/headers", "Headers + timing", "?url=https://example.com"),
            Endpoint("GET", "/v1/http/redirects", "Redirect chain", "?url=http://google.com"),
            Endpoint("GET", "/v1/tls/cert", "TLS certificate", "?host=example.com"),
            Endpoint("GET", "/v1/net/tcp-ping", "TCP connect latency", "?host=1.1.1.1&port=443"),
            Endpoint("GET", "/v1/net/port-check", "Port scan (tiny)", "?host=example.com&ports=22,80,443"),
        ],
    )
)
