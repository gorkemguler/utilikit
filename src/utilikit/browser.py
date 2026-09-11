"""Headless-Chromium manager for the capture tools (Playwright).

Entirely optional: install with ``pip install 'utilikit[browser]'`` then
``playwright install --with-deps chromium``. If Playwright or the browser binary
is missing, the capture endpoints return HTTP 503 with an install hint instead
of crashing the app.

RAM: each context is ~120-200 MB. ``UTILIKIT_BROWSER_CONCURRENCY`` (default 1)
caps how many run at once - keep it at 1 on a 2 GB Pi.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

from .config import get_settings
from .errors import FeatureUnavailable

_INSTALL_HINT = (
    "Capture tools need a browser. Install it with:  "
    "pip install 'utilikit[browser]' && playwright install --with-deps chromium"
)

_playwright: Any = None
_browser: Any = None
_lock = asyncio.Lock()
_sema: asyncio.Semaphore | None = None


def _semaphore() -> asyncio.Semaphore:
    global _sema
    if _sema is None:
        _sema = asyncio.Semaphore(max(1, get_settings().browser_concurrency))
    return _sema


async def available() -> bool:
    try:
        await _ensure_browser()
        return True
    except FeatureUnavailable:
        return False


async def _ensure_browser() -> Any:
    global _playwright, _browser
    if _browser is not None and _browser.is_connected():
        return _browser
    async with _lock:
        if _browser is not None and _browser.is_connected():
            return _browser
        try:
            from playwright.async_api import async_playwright
        except ModuleNotFoundError as exc:
            raise FeatureUnavailable(_INSTALL_HINT) from exc
        try:
            _playwright = await async_playwright().start()
            _browser = await _playwright.chromium.launch(
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
        except Exception as exc:  # pragma: no cover - environment dependent
            raise FeatureUnavailable(f"{_INSTALL_HINT}  ({exc})") from exc
        return _browser


@contextlib.asynccontextmanager
async def page(
    *,
    width: int = 1280,
    height: int = 800,
    dark: bool = False,
    scale: float = 1.0,
):
    settings = get_settings()
    browser = await _ensure_browser()
    async with _semaphore():
        context = await browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=scale,
            color_scheme="dark" if dark else "light",
            user_agent=settings.fetch_user_agent,
            java_script_enabled=True,
        )
        context.set_default_navigation_timeout(settings.browser_nav_timeout_seconds * 1000)
        context.set_default_timeout(settings.browser_timeout_seconds * 1000)
        pg = await context.new_page()
        try:
            yield pg
        finally:
            with contextlib.suppress(Exception):
                await context.close()


async def shutdown() -> None:
    global _playwright, _browser
    with contextlib.suppress(Exception):
        if _browser is not None:
            await _browser.close()
    with contextlib.suppress(Exception):
        if _playwright is not None:
            await _playwright.stop()
    _browser = _playwright = None
