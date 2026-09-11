"""Text transforms: slugify, case conversion, lorem, diff, markdown, stats, regex."""

from __future__ import annotations

import difflib
import random
import re
import unicodedata

from fastapi import APIRouter, Body, Query
from pydantic import BaseModel

from ..errors import ToolError
from ..registry import Endpoint, ToolInfo, register

router = APIRouter(prefix="/v1", tags=["text"])

_LOREM = [
    "lorem",
    "ipsum",
    "dolor",
    "sit",
    "amet",
    "consectetur",
    "adipiscing",
    "elit",
    "sed",
    "do",
    "eiusmod",
    "tempor",
    "incididunt",
    "ut",
    "labore",
    "et",
    "dolore",
    "magna",
    "aliqua",
    "ut",
    "enim",
    "ad",
    "minim",
    "veniam",
    "quis",
    "nostrud",
    "exercitation",
    "ullamco",
    "laboris",
    "nisi",
    "ut",
    "aliquip",
    "ex",
    "ea",
    "commodo",
    "consequat",
    "duis",
    "aute",
    "irure",
    "dolor",
    "in",
    "reprehenderit",
    "in",
    "voluptate",
    "velit",
    "esse",
    "cillum",
    "dolore",
    "eu",
    "fugiat",
    "nulla",
    "pariatur",
    "excepteur",
    "sint",
    "occaecat",
    "cupidatat",
    "non",
    "proident",
    "sunt",
    "in",
    "culpa",
    "qui",
    "officia",
    "deserunt",
    "mollit",
    "anim",
    "id",
    "est",
    "laborum",
]


class DiffIn(BaseModel):
    a: str
    b: str
    context: int = 3


def slugify_text(value: str, sep: str = "-", lower: bool = True, max_length: int = 0) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_-]+", sep, value).strip(sep)
    if lower:
        value = value.lower()
    if max_length and len(value) > max_length:
        value = value[:max_length].rstrip(sep)
    return value


@router.get("/slugify", summary="Make a URL-safe slug from text")
def slugify(
    text: str,
    separator: str = "-",
    lowercase: bool = True,
    max_length: int = Query(0, ge=0, le=512),
) -> dict:
    return {"slug": slugify_text(text, separator, lowercase, max_length)}


@router.get("/case", summary="Convert between camel/snake/kebab/pascal/constant/title cases")
def convert_case(text: str, to: str = "snake") -> dict:
    words = re.findall(r"[A-Za-z0-9]+", re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text))
    words = [w.lower() for w in words]
    if not words:
        return {"result": ""}
    mapping = {
        "snake": "_".join(words),
        "kebab": "-".join(words),
        "constant": "_".join(words).upper(),
        "camel": words[0] + "".join(w.capitalize() for w in words[1:]),
        "pascal": "".join(w.capitalize() for w in words),
        "title": " ".join(w.capitalize() for w in words),
        "sentence": (" ".join(words)).capitalize(),
        "lower": " ".join(words),
        "upper": " ".join(words).upper(),
    }
    if to not in mapping:
        raise ToolError(f"Unknown case {to!r}. Options: {sorted(mapping)}")
    return {"to": to, "result": mapping[to], "all": mapping}


@router.get("/lorem", summary="Generate placeholder text")
def lorem(
    paragraphs: int = Query(3, ge=1, le=50),
    sentences_per_paragraph: int = Query(4, ge=1, le=20),
    words_per_sentence: int = Query(12, ge=3, le=40),
    seed: int | None = None,
) -> dict:
    rng = random.Random(seed)
    out = []
    for _ in range(paragraphs):
        sents = []
        for _ in range(sentences_per_paragraph):
            s = [rng.choice(_LOREM) for _ in range(words_per_sentence)]
            sents.append(s[0].capitalize() + " " + " ".join(s[1:]) + ".")
        out.append(" ".join(sents))
    return {"text": "\n\n".join(out), "paragraphs": out}


@router.post("/diff", summary="Unified diff between two texts")
def diff(body: DiffIn) -> dict:
    a_lines = body.a.splitlines(keepends=True)
    b_lines = body.b.splitlines(keepends=True)
    ud = list(difflib.unified_diff(a_lines, b_lines, "a", "b", n=body.context))
    ratio = difflib.SequenceMatcher(None, body.a, body.b).ratio()
    return {"unified": "".join(ud), "similarity": round(ratio, 4), "changed": bool(ud)}


@router.post("/markdown", summary="Render Markdown to HTML")
def markdown(text: str = Body(..., embed=True), safe: bool = Body(True, embed=True)) -> dict:
    import mistune

    renderer = mistune.create_markdown(escape=safe, plugins=["strikethrough", "table", "url", "task_lists"])
    return {"html": renderer(text)}


@router.get("/text/stats", summary="Word / character / reading-time stats")
def text_stats(text: str) -> dict:
    words = re.findall(r"\b[\w'-]+\b", text)
    sentences = re.split(r"[.!?]+(?:\s|$)", text.strip())
    sentences = [s for s in sentences if s.strip()]
    return {
        "characters": len(text),
        "characters_no_spaces": len(re.sub(r"\s", "", text)),
        "words": len(words),
        "unique_words": len({w.lower() for w in words}),
        "sentences": len(sentences),
        "lines": text.count("\n") + 1 if text else 0,
        "reading_time_seconds": round(len(words) / 200 * 60),
    }


@router.get("/regex/test", summary="Test a regex against a string; returns all matches + groups")
def regex_test(
    pattern: str,
    text: str,
    ignorecase: bool = False,
    multiline: bool = False,
    dotall: bool = False,
) -> dict:
    flags = 0
    flags |= re.IGNORECASE if ignorecase else 0
    flags |= re.MULTILINE if multiline else 0
    flags |= re.DOTALL if dotall else 0
    try:
        rx = re.compile(pattern, flags)
    except re.error as exc:
        raise ToolError(f"Invalid regex: {exc}") from exc
    matches = []
    for m in rx.finditer(text):
        matches.append(
            {
                "match": m.group(0),
                "span": list(m.span()),
                "groups": list(m.groups()),
                "named": m.groupdict(),
            }
        )
    return {"count": len(matches), "matches": matches}


register(
    ToolInfo(
        key="text",
        title="Text utilities",
        category="Text & data",
        description="slugify, case conversion, lorem ipsum, unified diff, Markdown→HTML, text stats, regex tester.",
        router=router,
        endpoints=[
            Endpoint("GET", "/v1/slugify", "URL slug", "?text=Merhaba Dünya!"),
            Endpoint("GET", "/v1/case", "Convert case", "?text=helloWorld&to=kebab"),
            Endpoint("GET", "/v1/lorem", "Placeholder text", "?paragraphs=2"),
            Endpoint("POST", "/v1/diff", "Unified diff", '{"a":"foo\\n","b":"bar\\n"}'),
            Endpoint("POST", "/v1/markdown", "Markdown to HTML", '{"text":"# Hi **there**"}'),
            Endpoint("GET", "/v1/text/stats", "Text stats", "?text=the quick brown fox"),
            Endpoint("GET", "/v1/regex/test", "Regex tester", "?pattern=\\d+&text=a1b22"),
        ],
    )
)
