"""FastAPI application factory."""

from __future__ import annotations

import logging
import platform
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import __version__
from .config import get_settings
from .db import init_db
from .errors import ToolError, install_error_handlers
from .i18n import CATEGORY_TR, ENDPOINT_TR, TOOL_TR, UI_TR
from .jobs import jobs
from .ratelimit import RateLimitMiddleware
from .registry import as_dict, catalog, categories
from .security import REQUESTS, TOOL_HITS, require_key

log = logging.getLogger("utilikit")
_HERE = Path(__file__).resolve().parent
_STARTED = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    logging.basicConfig(level=s.log_level, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    s.ensure_dirs()
    init_db()
    log.info("utilikit %s starting on %s:%s (%d tools)", __version__, s.host, s.port, len(catalog()))
    try:
        yield
    finally:
        from . import browser

        await browser.shutdown()


def _index_view_models() -> list[dict]:
    """Catalogue entries plus their (optional) Turkish strings, for the index page."""
    out = []
    for info in catalog():
        tr = TOOL_TR.get(info.key, {})
        out.append(
            {
                "key": info.key,
                "category": info.category,
                "requires": info.requires,
                "title": {"en": info.title, "tr": tr.get("title", info.title)},
                "description": {"en": info.description, "tr": tr.get("description", info.description)},
                "endpoints": [
                    {
                        "method": e.method,
                        "path": e.path,
                        "example": e.example,
                        "summary": {"en": e.summary, "tr": ENDPOINT_TR.get(e.path, e.summary)},
                    }
                    for e in info.endpoints
                ],
            }
        )
    return out


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Utilikit",
        version=__version__,
        summary="A self-hostable HTTP toolbox: WHOIS, DNS, screenshots, PDF, image ops, codecs, QR and more.",
        lifespan=lifespan,
    )
    install_error_handlers(app)
    app.add_middleware(RateLimitMiddleware)

    templates = Jinja2Templates(directory=_HERE / "web" / "templates")
    app.mount("/static", StaticFiles(directory=_HERE / "web" / "static"), name="static")

    # Import tool modules -> they populate the registry.
    from . import tools  # noqa: F401

    for info in catalog():
        app.include_router(info.router, dependencies=[Depends(require_key)])
        if info.public_router is not None:
            app.include_router(info.public_router)

    # ---------------------------------------------------------------- meta
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "version": __version__,
                "tools": _index_view_models(),
                "categories": [{"en": c, "tr": CATEGORY_TR.get(c, c)} for c in categories()],
                "auth_required": bool(settings.keys),
                "browser_enabled": settings.browser_enabled,
                "ui": UI_TR,
                "tagline_tr": UI_TR["tagline"].format(categories=len(categories()), tools=len(catalog())),
            },
        )

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> dict:
        return {
            "status": "ok",
            "version": __version__,
            "uptime_seconds": int(time.time() - _STARTED),
            "python": platform.python_version(),
            "tools": len(catalog()),
        }

    @app.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
    def metrics() -> str:
        lines = [
            "# HELP utilikit_requests_total responses by status class",
            "# TYPE utilikit_requests_total counter",
        ]
        for cls, n in sorted(REQUESTS.items()):
            lines.append(f'utilikit_requests_total{{class="{cls}"}} {n}')
        lines.append("# HELP utilikit_tool_hits_total requests per tool group")
        lines.append("# TYPE utilikit_tool_hits_total counter")
        for seg, n in sorted(TOOL_HITS.items()):
            lines.append(f'utilikit_tool_hits_total{{tool="{seg}"}} {n}')
        lines.append(f"utilikit_uptime_seconds {int(time.time() - _STARTED)}")
        return "\n".join(lines) + "\n"

    @app.get("/v1/tools", tags=["meta"])
    def list_tools() -> dict:
        return {"count": len(catalog()), "categories": categories(), "tools": as_dict()}

    @app.get("/v1/jobs/{job_id}", tags=["meta"])
    def job_status(job_id: str) -> dict:
        job = jobs().get(job_id)
        if job is None:
            raise ToolError("Unknown or expired job id.", status_code=404, type="not_found")
        return job.as_dict()

    return app


app = create_app()
