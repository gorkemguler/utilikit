"""Importing this package registers every tool's router with the app.

Add a new tool: drop a module here that builds an ``APIRouter`` and calls
``utilikit.registry.register(ToolInfo(...))``, then add it to ``_MODULES``.
"""

from __future__ import annotations

from importlib import import_module

_MODULES = [
    "codec",
    "idgen",
    "text",
    "data_fmt",
    "time_tools",
    "color",
    "qr",
    "misc",
    "net_dns",
    "net_whois",
    "net_http",
    "web_meta",
    "media_image",
    "web_capture",
]

for _m in _MODULES:
    import_module(f"{__name__}.{_m}")
