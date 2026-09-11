"""Tool catalogue.

Each module under ``utilikit.tools`` builds a normal FastAPI ``APIRouter`` and
calls :func:`register` with a bit of metadata. The app mounts every router and
the HTML index / ``GET /v1/tools`` render the catalogue.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import APIRouter


@dataclass(slots=True)
class Endpoint:
    method: str
    path: str
    summary: str
    # A ready-to-run example (query string or short note) for the index page.
    example: str = ""


@dataclass(slots=True)
class ToolInfo:
    key: str
    title: str
    category: str
    description: str
    router: APIRouter
    endpoints: list[Endpoint] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)  # e.g. ["browser"], ["decode"]
    # Routes that must stay reachable WITHOUT an API key (shortener redirect,
    # request-bin capture - external callers can't send your key).
    public_router: APIRouter | None = None


_CATALOG: list[ToolInfo] = []


def register(info: ToolInfo) -> ToolInfo:
    _CATALOG.append(info)
    return info


def catalog() -> list[ToolInfo]:
    return sorted(_CATALOG, key=lambda t: (t.category, t.title))


def categories() -> list[str]:
    return sorted({t.category for t in _CATALOG})


def as_dict() -> list[dict]:
    return [
        {
            "key": t.key,
            "title": t.title,
            "category": t.category,
            "description": t.description,
            "requires": t.requires,
            "endpoints": [
                {"method": e.method, "path": e.path, "summary": e.summary, "example": e.example} for e in t.endpoints
            ],
        }
        for t in catalog()
    ]
