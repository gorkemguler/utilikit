"""Utilikit - a self-hostable HTTP toolbox API.

One FastAPI app that exposes ~45 small, focused endpoints (WHOIS, DNS,
screenshots, PDF, image transforms, codecs, hashing, QR, time/colour helpers,
a request bin, a URL shortener, …). Designed to run comfortably on a Raspberry
Pi 4 or a retired laptop.

Every tool module in ``utilikit.tools`` registers a normal ``APIRouter`` plus a
:class:`utilikit.registry.ToolInfo` used by the HTML index.
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__ = ["__version__"]
