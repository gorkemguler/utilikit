"""Screenshot / PDF / render tools (headless Chromium via Playwright - optional)."""

from __future__ import annotations

import base64
from urllib.parse import urlsplit

from fastapi import APIRouter, Body, Query, Response
from pydantic import BaseModel

from .. import browser
from ..config import get_settings
from ..errors import FeatureUnavailable, ToolError
from ..jobs import jobs
from ..registry import Endpoint, ToolInfo, register
from ..safefetch import assert_host_allowed

router = APIRouter(prefix="/v1", tags=["capture"])


def _guard_enabled() -> None:
    if not get_settings().browser_enabled:
        raise FeatureUnavailable("Capture tools are disabled (UTILIKIT_BROWSER_ENABLED=false).")


def _check_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ToolError("Give an absolute http(s) URL.")
    assert_host_allowed(parts.hostname)
    return url


async def _screenshot_bytes(
    url: str,
    width: int,
    height: int,
    full_page: bool,
    dark: bool,
    scale: float,
    wait_until: str,
    delay_ms: int,
    fmt: str,
) -> bytes:
    async with browser.page(width=width, height=height, dark=dark, scale=scale) as pg:
        await pg.goto(url, wait_until=wait_until)
        if delay_ms:
            await pg.wait_for_timeout(min(delay_ms, 10_000))
        return await pg.screenshot(full_page=full_page, type=fmt)


async def _pdf_bytes(url: str, paper: str, landscape: bool, background: bool, scale: float) -> bytes:
    async with browser.page(width=1280, height=900) as pg:
        await pg.goto(url, wait_until="networkidle")
        return await pg.pdf(
            format=paper, landscape=landscape, print_background=background, scale=scale, prefer_css_page_size=True
        )


async def _render_bytes(html: str, as_pdf: bool, width: int, height: int, dark: bool) -> bytes:
    async with browser.page(width=width, height=height, dark=dark) as pg:
        await pg.set_content(html, wait_until="load")
        return await pg.pdf(format="A4", print_background=True) if as_pdf else await pg.screenshot(full_page=True)


@router.get("/screenshot", summary="Screenshot a URL (PNG/JPEG). Add async=true for a job.")
async def screenshot(
    url: str,
    width: int = Query(1280, ge=200, le=3840),
    height: int = Query(800, ge=200, le=4320),
    full_page: bool = False,
    dark: bool = False,
    scale: float = Query(1.0, ge=0.5, le=3.0),
    wait_until: str = Query("load", pattern="^(load|domcontentloaded|networkidle)$"),
    delay_ms: int = Query(0, ge=0, le=10000),
    format: str = Query("png", pattern="^(png|jpeg)$"),
    async_: bool = Query(False, alias="async"),
):
    _guard_enabled()
    _check_url(url)
    args = (url, width, height, full_page, dark, scale, wait_until, delay_ms, format)
    if async_:
        job = await jobs().submit(
            "screenshot",
            lambda: _as_data_url(_screenshot_bytes(*args), "image/" + format),
        )
        return job.as_dict()
    data = await _screenshot_bytes(*args)
    return Response(data, media_type=f"image/{format}")


@router.get("/pdf", summary="Render a URL to PDF")
async def url_to_pdf(
    url: str,
    paper: str = Query("A4"),
    landscape: bool = False,
    background: bool = True,
    scale: float = Query(1.0, ge=0.1, le=2.0),
    async_: bool = Query(False, alias="async"),
):
    _guard_enabled()
    _check_url(url)
    if async_:
        job = await jobs().submit(
            "pdf", lambda: _as_data_url(_pdf_bytes(url, paper, landscape, background, scale), "application/pdf")
        )
        return job.as_dict()
    data = await _pdf_bytes(url, paper, landscape, background, scale)
    return Response(data, media_type="application/pdf", headers={"content-disposition": 'inline; filename="page.pdf"'})


class RenderIn(BaseModel):
    html: str
    as_pdf: bool = False
    width: int = 1280
    height: int = 800
    dark: bool = False


@router.post("/render", summary="Render raw HTML to PNG or PDF (no SSRF surface)")
async def render(body: RenderIn = Body(...)):
    _guard_enabled()
    if len(body.html) > 2_000_000:
        raise ToolError("HTML payload too large (> 2 MB).")
    data = await _render_bytes(body.html, body.as_pdf, body.width, body.height, body.dark)
    return Response(data, media_type="application/pdf" if body.as_pdf else "image/png")


@router.get("/jobs/{job_id}/result", summary="Fetch a finished capture job's binary result")
def job_result(job_id: str):
    job = jobs().get(job_id)
    if job is None:
        raise ToolError("Unknown or expired job.", status_code=404, type="not_found")
    if job.state != "done":
        raise ToolError(f"Job is {job.state}.", status_code=409, detail={"state": job.state, "error": job.error})
    mime, b64 = job.result
    return Response(base64.b64decode(b64), media_type=mime)


async def _as_data_url(coro, mime: str) -> tuple[str, str]:
    data = await coro
    return mime, base64.b64encode(data).decode()


register(
    ToolInfo(
        key="capture",
        title="Screenshots & PDF",
        category="Web capture",
        description=(
            "Full/viewport screenshots (PNG/JPEG), URL to PDF, and raw-HTML render. "
            "Sync or async (job) mode. Needs the 'browser' extra."
        ),
        router=router,
        requires=["browser"],
        endpoints=[
            Endpoint("GET", "/v1/screenshot", "Screenshot a URL", "?url=https://example.com&full_page=true&dark=true"),
            Endpoint("GET", "/v1/pdf", "URL to PDF", "?url=https://example.com&paper=A4"),
            Endpoint("POST", "/v1/render", "Render raw HTML", '{"html":"<h1>hi</h1>","as_pdf":true}'),
            Endpoint("GET", "/v1/jobs/{id}/result", "Async job binary", ""),
        ],
    )
)
