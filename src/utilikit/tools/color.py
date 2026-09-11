"""Colour helpers: format conversion, WCAG contrast, random palettes."""

from __future__ import annotations

import colorsys
import random

from fastapi import APIRouter, Query

from ..errors import ToolError
from ..registry import Endpoint, ToolInfo, register

router = APIRouter(prefix="/v1", tags=["color"])


def parse_color(value: str) -> tuple[int, int, int]:
    v = value.strip().lower()
    if v.startswith("#"):
        v = v[1:]
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    if len(v) == 6:
        try:
            return (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16))
        except ValueError:
            pass
    if v.startswith("rgb"):
        nums = [int(float(x)) for x in v.strip("rgba() ").split(",")[:3]]
        if len(nums) == 3:
            return tuple(max(0, min(255, n)) for n in nums)  # type: ignore[return-value]
    raise ToolError(f"Could not parse colour {value!r}. Use #rrggbb, #rgb or rgb(r,g,b).")


def _rel_luminance(rgb: tuple[int, int, int]) -> float:
    def chan(c: float) -> float:
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (chan(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _formats(rgb: tuple[int, int, int]) -> dict:
    r, g, b = rgb
    hue, lit, sat = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    hh, ss, vv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return {
        "hex": f"#{r:02x}{g:02x}{b:02x}",
        "rgb": f"rgb({r}, {g}, {b})",
        "rgb_tuple": [r, g, b],
        "hsl": f"hsl({round(hue * 360)}, {round(sat * 100)}%, {round(lit * 100)}%)",
        "hsv": f"hsv({round(hh * 360)}, {round(ss * 100)}%, {round(vv * 100)}%)",
        "luminance": round(_rel_luminance(rgb), 4),
    }


@router.get("/color/convert", summary="Convert a colour to hex / rgb / hsl / hsv")
def convert(color: str) -> dict:
    return _formats(parse_color(color))


@router.get("/color/contrast", summary="WCAG contrast ratio between two colours")
def contrast(foreground: str, background: str) -> dict:
    l1 = _rel_luminance(parse_color(foreground))
    l2 = _rel_luminance(parse_color(background))
    ratio = (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)
    return {
        "ratio": round(ratio, 2),
        "AA_normal": ratio >= 4.5,
        "AA_large": ratio >= 3.0,
        "AAA_normal": ratio >= 7.0,
        "AAA_large": ratio >= 4.5,
    }


@router.get("/color/palette", summary="Generate a harmonious random palette")
def palette(
    count: int = Query(5, ge=2, le=12),
    scheme: str = Query("random", pattern="^(random|analogous|complementary|triadic|monochrome)$"),
    seed: int | None = None,
) -> dict:
    rng = random.Random(seed)
    base_h = rng.random()
    s, v = 0.55 + rng.random() * 0.35, 0.65 + rng.random() * 0.3
    hues: list[float]
    if scheme == "analogous":
        hues = [(base_h + i * 0.05) % 1 for i in range(count)]
    elif scheme == "complementary":
        hues = [base_h if i % 2 == 0 else (base_h + 0.5) % 1 for i in range(count)]
    elif scheme == "triadic":
        hues = [(base_h + (i % 3) / 3) % 1 for i in range(count)]
    elif scheme == "monochrome":
        hues = [base_h] * count
    else:
        hues = [rng.random() for _ in range(count)]
    colors = []
    for i, h in enumerate(hues):
        vv = v if scheme != "monochrome" else 0.3 + 0.6 * (i + 1) / count
        r, g, b = (round(x * 255) for x in colorsys.hsv_to_rgb(h, s, vv))
        colors.append(_formats((r, g, b)))
    return {"scheme": scheme, "colors": colors}


register(
    ToolInfo(
        key="color",
        title="Colour tools",
        category="Time & colour",
        description="Convert between hex/rgb/hsl/hsv, WCAG contrast ratios, random harmonious palettes.",
        router=router,
        endpoints=[
            Endpoint("GET", "/v1/color/convert", "Convert colour", "?color=%233b82f6"),
            Endpoint("GET", "/v1/color/contrast", "Contrast ratio", "?foreground=%23fff&background=%23555"),
            Endpoint("GET", "/v1/color/palette", "Random palette", "?count=5&scheme=analogous"),
        ],
    )
)
