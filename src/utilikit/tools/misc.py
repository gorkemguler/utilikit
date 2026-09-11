"""Grab bag: user-agent parser, MIME guess, Luhn check, request bin, URL shortener."""

from __future__ import annotations

import json
import mimetypes
import re
import secrets

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from ..config import get_settings
from ..db import cursor
from ..errors import ToolError
from ..registry import Endpoint, ToolInfo, register
from ..safefetch import assert_host_allowed

router = APIRouter(prefix="/v1", tags=["misc"])
public = APIRouter(tags=["misc"])

# ---------------------------------------------------------------- user agent
_UA_OS = [
    (r"Windows NT 10\.0", "Windows 10/11"),
    (r"Windows NT 6\.1", "Windows 7"),
    (r"Mac OS X (\d+[._]\d+)", "macOS"),
    (r"Android (\d+)", "Android"),
    (r"(iPhone|iPad); CPU .*OS (\d+)", "iOS"),
    (r"Linux", "Linux"),
]
_UA_BROWSER = [
    (r"Edg/(\d+)", "Edge"),
    (r"OPR/(\d+)", "Opera"),
    (r"Firefox/(\d+)", "Firefox"),
    (r"Chrome/(\d+)", "Chrome"),
    (r"Version/(\d+).*Safari", "Safari"),
    (r"curl/(\d+)", "curl"),
    (r"Wget/(\d+)", "Wget"),
    (r"bot|crawler|spider|slurp", "Bot"),
]


@router.get("/ua/parse", summary="Parse a User-Agent string")
def ua_parse(user_agent: str) -> dict:
    ua = user_agent
    os_name = next((name for rx, name in _UA_OS if re.search(rx, ua)), "unknown")
    browser = next((name for rx, name in _UA_BROWSER if re.search(rx, ua, re.I)), "unknown")
    m = next((re.search(rx, ua, re.I) for rx, name in _UA_BROWSER if re.search(rx, ua, re.I)), None)
    return {
        "user_agent": ua,
        "os": os_name,
        "browser": browser,
        "browser_version": (m.group(1) if m and m.groups() else None),
        "mobile": bool(re.search(r"Mobi|Android|iPhone|iPad", ua)),
        "bot": bool(re.search(r"bot|crawler|spider|slurp|curl|wget", ua, re.I)),
    }


# ---------------------------------------------------------------------- mime
@router.get("/mime", summary="Guess a MIME type from a filename or extension")
def mime_guess(filename: str) -> dict:
    guessed, encoding = mimetypes.guess_type(filename if "." in filename else f"x.{filename}")
    return {"filename": filename, "mime_type": guessed or "application/octet-stream", "encoding": encoding}


# ---------------------------------------------------------------------- luhn
@router.get("/luhn", summary="Validate a number with the Luhn checksum (cards, IMEI, …)")
def luhn(number: str) -> dict:
    digits = [int(c) for c in re.sub(r"\D", "", number)]
    if len(digits) < 2:
        raise ToolError("Need at least two digits.")
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return {"input_digits": len(digits), "valid": checksum % 10 == 0, "checksum": checksum}


# ------------------------------------------------------------------ request bin
@router.get("/bin/new", summary="Create a fresh request-bin id")
def bin_new() -> dict:
    bid = secrets.token_urlsafe(9)
    base = get_settings().public_base_url.rstrip("/")
    return {"bin_id": bid, "capture_url": f"{base}/bin/{bid}" if base else f"/bin/{bid}"}


@router.get("/bin/{bin_id}", summary="List captured requests for a bin (newest first)")
def bin_list(bin_id: str, limit: int = 50) -> dict:
    with cursor() as cur:
        rows = cur.execute(
            "SELECT ts,method,path,query,headers,body,remote FROM bin_requests WHERE bin_id=? ORDER BY id DESC LIMIT ?",
            (bin_id, max(1, min(limit, 200))),
        ).fetchall()
    return {
        "bin_id": bin_id,
        "count": len(rows),
        "requests": [
            {
                "ts": r["ts"],
                "method": r["method"],
                "path": r["path"],
                "query": r["query"],
                "headers": json.loads(r["headers"]),
                "body": r["body"],
                "remote": r["remote"],
            }
            for r in rows
        ],
    }


@public.api_route(
    "/bin/{bin_id}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    summary="Capture any request into a bin (point webhooks here)",
    include_in_schema=False,
)
async def bin_capture(bin_id: str, request: Request) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,64}", bin_id):
        raise ToolError("Bad bin id.")
    raw = (await request.body())[:64_000]
    keep = get_settings().bin_max_requests
    with cursor() as cur:
        cur.execute(
            "INSERT INTO bin_requests(bin_id,method,path,query,headers,body,remote) VALUES (?,?,?,?,?,?,?)",
            (
                bin_id,
                request.method,
                request.url.path,
                str(request.url.query),
                json.dumps(dict(request.headers)),
                raw.decode("utf-8", "replace"),
                request.client.host if request.client else "",
            ),
        )
        cur.execute(
            "DELETE FROM bin_requests WHERE bin_id=? AND id NOT IN "
            "(SELECT id FROM bin_requests WHERE bin_id=? ORDER BY id DESC LIMIT ?)",
            (bin_id, bin_id, keep),
        )
    return {"captured": True, "bin_id": bin_id}


# ------------------------------------------------------------------ shortener
class ShortIn(BaseModel):
    url: str
    code: str | None = None


@router.post("/short", summary="Create a short link")
def short_create(body: ShortIn) -> dict:
    if not get_settings().shortener_enabled:
        raise ToolError("Shortener is disabled (UTILIKIT_SHORTENER_ENABLED=false).", status_code=403)
    from urllib.parse import urlsplit

    parts = urlsplit(body.url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ToolError("url must be an absolute http(s) URL.")
    assert_host_allowed(parts.hostname)  # keep the shortener from proxying internal hosts
    code = body.code or secrets.token_urlsafe(5).replace("_", "").replace("-", "")[:7] or secrets.token_hex(4)
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,32}", code):
        raise ToolError("code must be 3-32 url-safe characters.")
    with cursor() as cur:
        exists = cur.execute("SELECT 1 FROM shortlinks WHERE code=?", (code,)).fetchone()
        if exists:
            raise ToolError(f"code {code!r} is taken.", status_code=409)
        cur.execute("INSERT INTO shortlinks(code,url) VALUES (?,?)", (code, body.url))
    base = get_settings().public_base_url.rstrip("/")
    return {"code": code, "short_url": f"{base}/s/{code}" if base else f"/s/{code}", "target": body.url}


@router.get("/short/{code}", summary="Look up a short link (no redirect)")
def short_info(code: str) -> dict:
    with cursor() as cur:
        row = cur.execute("SELECT url,created_at,hits FROM shortlinks WHERE code=?", (code,)).fetchone()
    if row is None:
        raise ToolError("Unknown code.", status_code=404, type="not_found")
    return {"code": code, "target": row["url"], "created_at": row["created_at"], "hits": row["hits"]}


@public.get("/s/{code}", include_in_schema=False)
def short_redirect(code: str) -> RedirectResponse:
    with cursor() as cur:
        row = cur.execute("SELECT url FROM shortlinks WHERE code=?", (code,)).fetchone()
        if row is None:
            raise ToolError("Unknown short link.", status_code=404, type="not_found")
        cur.execute("UPDATE shortlinks SET hits = hits + 1 WHERE code=?", (code,))
    return RedirectResponse(row["url"], status_code=302)


register(
    ToolInfo(
        key="misc",
        title="Web helpers, request bin & shortener",
        category="Web helpers",
        description=(
            "User-agent parser, MIME guess, Luhn check, a webhook request bin, and a URL shortener (SQLite-backed)."
        ),
        router=router,
        public_router=public,
        endpoints=[
            Endpoint("GET", "/v1/ua/parse", "Parse a UA string", "?user_agent=Mozilla/5.0 ... Chrome/125"),
            Endpoint("GET", "/v1/mime", "Guess MIME type", "?filename=archive.tar.gz"),
            Endpoint("GET", "/v1/luhn", "Luhn checksum", "?number=4242424242424242"),
            Endpoint("GET", "/v1/bin/new", "New request bin", ""),
            Endpoint("ANY", "/bin/{id}", "Capture a request (public)", "point a webhook here"),
            Endpoint("GET", "/v1/bin/{id}", "List captured requests", ""),
            Endpoint("POST", "/v1/short", "Create short link", '{"url":"https://example.com/very/long"}'),
            Endpoint("GET", "/s/{code}", "Redirect (public)", ""),
        ],
    )
)
