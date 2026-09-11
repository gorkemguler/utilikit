"""Page metadata: unfurl (OG/Twitter/oEmbed/favicon), readability, link extraction, HTML→text."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
from fastapi import APIRouter, Query

from ..errors import ToolError
from ..registry import Endpoint, ToolInfo, register
from ..safefetch import fetch

router = APIRouter(prefix="/v1", tags=["web"])

_MAX_HTML = 3_000_000


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html[:_MAX_HTML], "lxml")


def _meta(soup: BeautifulSoup, *names: str) -> str:
    for n in names:
        tag = soup.find("meta", attrs={"property": n}) or soup.find("meta", attrs={"name": n})
        if tag and tag.get("content"):
            return tag["content"].strip()
    return ""


@router.get("/unfurl", summary="Extract title, description, OpenGraph/Twitter cards, favicon, canonical")
async def unfurl(url: str) -> dict:
    res = await fetch(url)
    if "html" not in res.content_type and "xml" not in res.content_type:
        raise ToolError(f"Expected HTML, got {res.content_type or 'unknown'}.", status_code=415)
    soup = _soup(res.text)
    base = res.url

    title = _meta(soup, "og:title", "twitter:title") or (
        soup.title.string.strip() if soup.title and soup.title.string else ""
    )
    desc = _meta(soup, "og:description", "twitter:description", "description")
    image = _meta(soup, "og:image", "twitter:image", "twitter:image:src")
    canonical = ""
    link_canonical = soup.find("link", rel=lambda v: v and "canonical" in v)
    if link_canonical and link_canonical.get("href"):
        canonical = urljoin(base, link_canonical["href"])

    icons = []
    for link in soup.find_all("link", rel=True):
        rels = " ".join(link["rel"]).lower()
        if "icon" in rels and link.get("href"):
            icons.append({"rel": rels, "href": urljoin(base, link["href"]), "sizes": link.get("sizes", "")})
    if not icons:
        icons.append({"rel": "default", "href": urljoin(base, "/favicon.ico"), "sizes": ""})

    oembed = ""
    oe = soup.find("link", type=re.compile("oembed"))
    if oe and oe.get("href"):
        oembed = urljoin(base, oe["href"])

    return {
        "url": base,
        "status_code": res.status_code,
        "site_name": _meta(soup, "og:site_name"),
        "title": title,
        "description": desc,
        "image": urljoin(base, image) if image else "",
        "type": _meta(soup, "og:type"),
        "canonical": canonical,
        "favicons": icons,
        "oembed": oembed,
        "lang": (soup.html.get("lang", "") if soup.html else ""),
        "themes": {
            "color": _meta(soup, "theme-color"),
        },
    }


@router.get("/readability", summary="Extract the main article text from a page")
async def readability(url: str, as_markdown: bool = Query(False)) -> dict:
    res = await fetch(url)
    soup = _soup(res.text)
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()

    candidates = soup.find_all(["article", "main"]) or soup.find_all(
        "div", attrs={"class": re.compile(r"(content|article|post|entry|story)", re.I)}
    )
    node = max(candidates, key=lambda n: len(n.get_text()), default=None) or soup.body or soup
    paragraphs = [p.get_text(" ", strip=True) for p in node.find_all(["p", "li", "h2", "h3", "blockquote"])]
    paragraphs = [p for p in paragraphs if len(p) > 25]
    text = "\n\n".join(paragraphs) if paragraphs else node.get_text("\n", strip=True)

    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    if as_markdown:
        text = f"# {title}\n\n{text}" if title else text
    words = len(re.findall(r"\w+", text))
    return {
        "url": res.url,
        "title": title,
        "text": text[:200_000],
        "word_count": words,
        "reading_time_min": max(1, round(words / 200)),
        "format": "markdown" if as_markdown else "text",
    }


@router.get("/links", summary="Extract and classify every link on a page")
async def links(url: str) -> dict:
    res = await fetch(url)
    soup = _soup(res.text)
    host = urlsplit(res.url).hostname or ""
    internal, external, other = [], [], []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#"):
            continue
        absu = urljoin(res.url, href)
        if absu in seen:
            continue
        seen.add(absu)
        parts = urlsplit(absu)
        entry = {"url": absu, "text": a.get_text(" ", strip=True)[:120], "rel": a.get("rel", [])}
        if parts.scheme not in {"http", "https"}:
            other.append(entry)
        elif parts.hostname == host:
            internal.append(entry)
        else:
            external.append(entry)
    return {
        "url": res.url,
        "counts": {"internal": len(internal), "external": len(external), "other": len(other)},
        "internal": internal[:500],
        "external": external[:500],
        "other": other[:200],
    }


@router.get("/html2text", summary="Strip a page (or fetched HTML) down to plain text")
async def html2text(url: str) -> dict:
    res = await fetch(url)
    soup = _soup(res.text)
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = re.sub(r"\n{3,}", "\n\n", soup.get_text("\n", strip=True))
    return {"url": res.url, "text": text[:300_000], "chars": len(text)}


@router.get("/favicon", summary="Resolve the best favicon URL for a site")
async def favicon(url: str) -> dict:
    res = await fetch(url)
    soup = _soup(res.text)
    best = ""
    best_size = -1
    for link in soup.find_all("link", rel=True, href=True):
        if "icon" not in " ".join(link["rel"]).lower():
            continue
        sizes = link.get("sizes", "")
        m = re.match(r"(\d+)", sizes)
        size = int(m.group(1)) if m else 0
        if size > best_size:
            best_size, best = size, urljoin(res.url, link["href"])
    if not best:
        best = urljoin(res.url, "/favicon.ico")
    return {"site": res.url, "favicon": best, "declared_size": best_size if best_size > 0 else None}


register(
    ToolInfo(
        key="web_meta",
        title="Page metadata & extraction",
        category="Web helpers",
        description=(
            "Unfurl a URL (OG/Twitter/oEmbed/favicon/canonical), pull the main article "
            "text, list & classify links, HTML to text. SSRF-guarded."
        ),
        router=router,
        endpoints=[
            Endpoint("GET", "/v1/unfurl", "Link preview data", "?url=https://github.com"),
            Endpoint("GET", "/v1/readability", "Main article text", "?url=https://example.com/post&as_markdown=true"),
            Endpoint("GET", "/v1/links", "Extract links", "?url=https://example.com"),
            Endpoint("GET", "/v1/html2text", "HTML to text", "?url=https://example.com"),
            Endpoint("GET", "/v1/favicon", "Best favicon URL", "?url=https://github.com"),
        ],
    )
)
