"""Image tools: transform, thumbnail, EXIF read/strip, colour palette, OG card."""

from __future__ import annotations

import io

from fastapi import APIRouter, File, Query, Response, UploadFile
from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps
from PIL.ExifTags import GPSTAGS, TAGS

from ..errors import ToolError
from ..registry import Endpoint, ToolInfo, register
from ..safefetch import fetch

router = APIRouter(prefix="/v1", tags=["image"])

_MAX_PIXELS = 40_000_000
_FMT = {"png": "PNG", "jpeg": "JPEG", "jpg": "JPEG", "webp": "WEBP", "gif": "GIF", "bmp": "BMP"}
_MIME = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp", "GIF": "image/gif", "BMP": "image/bmp"}


async def _load(file: UploadFile | None, url: str | None) -> Image.Image:
    if file is not None:
        raw = await file.read()
    elif url:
        res = await fetch(url)
        if not res.content_type.startswith("image/"):
            raise ToolError(f"URL is {res.content_type or 'not an image'}.", status_code=415)
        raw = res.content
    else:
        raise ToolError("Provide an uploaded 'file' or a '?url='.")
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception as exc:
        raise ToolError(f"Unreadable image: {exc}") from exc
    if img.width * img.height > _MAX_PIXELS:
        raise ToolError("Image is too large (> 40 MP).")
    return img


def _encode(img: Image.Image, fmt: str, quality: int) -> tuple[bytes, str]:
    pil_fmt = _FMT.get(fmt.lower())
    if not pil_fmt:
        raise ToolError(f"Unknown format {fmt!r}. Options: {sorted(_FMT)}")
    if pil_fmt == "JPEG" and img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    params = {"quality": quality} if pil_fmt in ("JPEG", "WEBP") else {}
    img.save(buf, pil_fmt, **params)
    return buf.getvalue(), _MIME[pil_fmt]


@router.post("/image/transform", summary="Resize / convert / re-compress an image (upload or ?url=)")
async def transform(
    file: UploadFile | None = File(None),
    url: str | None = Query(None),
    width: int | None = Query(None, ge=1, le=10000),
    height: int | None = Query(None, ge=1, le=10000),
    fit: str = Query("contain", pattern="^(contain|cover|stretch)$"),
    format: str = Query("png"),
    quality: int = Query(85, ge=1, le=100),
    grayscale: bool = False,
) -> Response:
    img = await _load(file, url)
    img = ImageOps.exif_transpose(img)
    if grayscale:
        img = ImageOps.grayscale(img)
    if width or height:
        tw = width or img.width
        th = height or img.height
        if fit == "cover":
            img = ImageOps.fit(img, (tw, th), Image.LANCZOS)
        elif fit == "stretch":
            img = img.resize((tw, th), Image.LANCZOS)
        else:
            img.thumbnail((tw, th), Image.LANCZOS)
    body, mime = _encode(img, format, quality)
    return Response(body, media_type=mime, headers={"x-image-size": f"{img.width}x{img.height}"})


@router.post("/image/thumbnail", summary="Square-crop thumbnail")
async def thumbnail(
    file: UploadFile | None = File(None),
    url: str | None = Query(None),
    size: int = Query(256, ge=16, le=2000),
    format: str = Query("webp"),
) -> Response:
    img = ImageOps.exif_transpose(await _load(file, url))
    img = ImageOps.fit(img, (size, size), Image.LANCZOS)
    body, mime = _encode(img, format, 82)
    return Response(body, media_type=mime)


@router.post("/image/exif", summary="Read EXIF / metadata from an image")
async def exif_read(file: UploadFile | None = File(None), url: str | None = Query(None)) -> dict:
    img = await _load(file, url)
    exif = img.getexif()
    data: dict = {}
    for tag_id, value in exif.items():
        name = TAGS.get(tag_id, str(tag_id))
        data[name] = _jsonable(value)
    gps = {}
    if 34853 in exif:
        for k, v in exif.get_ifd(34853).items():
            gps[GPSTAGS.get(k, str(k))] = _jsonable(v)
    return {
        "format": img.format,
        "mode": img.mode,
        "size": [img.width, img.height],
        "has_exif": bool(data),
        "exif": data,
        "gps": gps,
    }


@router.post("/image/strip-exif", summary="Return the image with all metadata removed")
async def exif_strip(
    file: UploadFile | None = File(None),
    url: str | None = Query(None),
    format: str = Query("jpeg"),
) -> Response:
    img = ImageOps.exif_transpose(await _load(file, url))
    clean = Image.new(img.mode, img.size)
    clean.putdata(list(img.getdata()))
    body, mime = _encode(clean, format, 92)
    return Response(body, media_type=mime)


@router.post("/image/palette", summary="Dominant colours of an image")
async def palette(
    file: UploadFile | None = File(None),
    url: str | None = Query(None),
    colors: int = Query(6, ge=2, le=16),
) -> dict:
    img = (await _load(file, url)).convert("RGB")
    img.thumbnail((200, 200))
    quant = img.quantize(colors=colors, method=Image.Quantize.FASTOCTREE)
    pal = quant.getpalette()
    counts = sorted(quant.getcolors(), reverse=True)
    out = []
    for count, idx in counts[:colors]:
        r, g, b = pal[idx * 3 : idx * 3 + 3]
        out.append({"hex": f"#{r:02x}{g:02x}{b:02x}", "rgb": [r, g, b], "weight": count})
    return {"colors": out}


@router.get("/og-image", summary="Generate a social/OpenGraph card PNG (no browser needed)")
def og_image(
    title: str,
    subtitle: str = "",
    theme: str = Query("dark", pattern="^(dark|light|blue|green)$"),
    width: int = Query(1200, ge=400, le=2000),
    height: int = Query(630, ge=200, le=1200),
) -> Response:
    palettes = {
        "dark": ("#0f1216", "#e6edf3", "#8b98a5", "#4fc3f7"),
        "light": ("#ffffff", "#111418", "#5a6672", "#2563eb"),
        "blue": ("#0b3a66", "#ffffff", "#bcd8f2", "#8ee3ff"),
        "green": ("#0b3d2e", "#eafff5", "#a7e8cf", "#6ee7b7"),
    }
    bg, fg, muted, accent = palettes[theme]
    img = Image.new("RGB", (width, height), ImageColor.getrgb(bg))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 14, height], fill=ImageColor.getrgb(accent))

    def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        try:
            return ImageFont.load_default(size=size)
        except TypeError:  # very old Pillow
            return ImageFont.load_default()

    _wrap_text(d, title, font(64), fg, (70, 90), width - 140, line_gap=14)
    if subtitle:
        _wrap_text(d, subtitle, font(34), muted, (70, height - 170), width - 140, line_gap=8, max_lines=2)
    d.text((70, height - 70), "utilikit", font=font(26), fill=ImageColor.getrgb(accent))

    buf = io.BytesIO()
    img.save(buf, "PNG")
    return Response(buf.getvalue(), media_type="image/png")


def _wrap_text(draw, text, fnt, color, xy, max_width, line_gap=10, max_lines=4):
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
        if len(lines) >= max_lines:
            break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    x, y = xy
    try:
        lh = fnt.size + line_gap
    except AttributeError:
        lh = 20 + line_gap
    for ln in lines[:max_lines]:
        draw.text((x, y), ln, font=fnt, fill=ImageColor.getrgb(color))
        y += lh


def _jsonable(v):
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace") if len(v) < 256 else f"<{len(v)} bytes>"
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    try:
        import json

        json.dumps(v)
        return v
    except (TypeError, ValueError):
        return str(v)


register(
    ToolInfo(
        key="image",
        title="Image processing",
        category="Media",
        description=(
            "Resize/convert/re-compress, square thumbnails, read & strip EXIF, "
            "colour palette, and a browserless OpenGraph card generator."
        ),
        router=router,
        endpoints=[
            Endpoint("POST", "/v1/image/transform", "Resize/convert", "?url=...&width=800&format=webp"),
            Endpoint("POST", "/v1/image/thumbnail", "Square thumbnail", "?url=...&size=256"),
            Endpoint("POST", "/v1/image/exif", "Read EXIF", "multipart file=@photo.jpg"),
            Endpoint("POST", "/v1/image/strip-exif", "Strip metadata", "multipart file=@photo.jpg"),
            Endpoint("POST", "/v1/image/palette", "Dominant colours", "?url=..."),
            Endpoint("GET", "/v1/og-image", "Social card PNG", "?title=Hello&subtitle=World&theme=blue"),
        ],
    )
)
