"""QR codes and 1-D barcodes."""

from __future__ import annotations

import io

from fastapi import APIRouter, File, Query, Response, UploadFile

from ..errors import FeatureUnavailable, ToolError
from ..registry import Endpoint, ToolInfo, register

router = APIRouter(prefix="/v1", tags=["qr"])

_EC = {"L": "ERROR_CORRECT_L", "M": "ERROR_CORRECT_M", "Q": "ERROR_CORRECT_Q", "H": "ERROR_CORRECT_H"}


@router.get("/qr", summary="Generate a QR code (PNG or SVG)")
def qr_generate(
    text: str,
    format: str = Query("png", pattern="^(png|svg)$"),
    scale: int = Query(8, ge=1, le=40),
    border: int = Query(2, ge=0, le=16),
    ec: str = Query("M", pattern="^[LMQH]$"),
) -> Response:
    import qrcode

    qr = qrcode.QRCode(
        error_correction=getattr(qrcode.constants, _EC[ec]),
        box_size=scale,
        border=border,
    )
    qr.add_data(text)
    qr.make(fit=True)

    if format == "svg":
        import qrcode.image.svg

        img = qr.make_image(image_factory=qrcode.image.svg.SvgImage)
        buf = io.BytesIO()
        img.save(buf)
        return Response(buf.getvalue(), media_type="image/svg+xml")

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(buf.getvalue(), media_type="image/png")


@router.post("/qr/decode", summary="Decode QR / barcodes from an uploaded image (needs the 'decode' extra)")
async def qr_decode(file: UploadFile = File(...)) -> dict:
    try:
        from pyzbar.pyzbar import decode as zbar_decode
    except Exception as exc:  # ModuleNotFoundError or missing libzbar
        raise FeatureUnavailable(
            "Decoding needs:  pip install 'utilikit[decode]'  and the system 'libzbar0' library."
        ) from exc
    from PIL import Image

    raw = await file.read()
    try:
        img = Image.open(io.BytesIO(raw))
    except Exception as exc:
        raise ToolError(f"Not a readable image: {exc}") from exc
    results = [
        {
            "type": d.type,
            "data": d.data.decode("utf-8", "replace"),
            "rect": {"x": d.rect.left, "y": d.rect.top, "w": d.rect.width, "h": d.rect.height},
        }
        for d in zbar_decode(img)
    ]
    return {"count": len(results), "symbols": results}


@router.get("/barcode", summary="Generate a 1-D barcode (code128, ean13, ean8, code39, …) as SVG or PNG")
def barcode_generate(
    text: str,
    symbology: str = Query("code128"),
    format: str = Query("svg", pattern="^(svg|png)$"),
) -> Response:
    import barcode
    from barcode.writer import ImageWriter, SVGWriter

    try:
        cls = barcode.get_barcode_class(symbology)
    except barcode.errors.BarcodeNotFoundError as exc:
        raise ToolError(f"Unknown symbology {symbology!r}. Try: {', '.join(barcode.PROVIDED_BARCODES)}") from exc

    try:
        if format == "png":
            obj = cls(text, writer=ImageWriter())
            buf = io.BytesIO()
            obj.write(buf)
            return Response(buf.getvalue(), media_type="image/png")
        obj = cls(text, writer=SVGWriter())
        buf = io.BytesIO()
        obj.write(buf)
        return Response(buf.getvalue(), media_type="image/svg+xml")
    except barcode.errors.BarcodeError as exc:
        raise ToolError(f"{symbology} rejected {text!r}: {exc}") from exc


register(
    ToolInfo(
        key="qr",
        title="QR & barcodes",
        category="Media",
        description="Generate QR codes (PNG/SVG) and 1-D barcodes; decode QR/barcodes from an image (optional extra).",
        router=router,
        requires=["decode (for /v1/qr/decode)"],
        endpoints=[
            Endpoint("GET", "/v1/qr", "Generate QR", "?text=https://example.com&format=svg"),
            Endpoint("POST", "/v1/qr/decode", "Decode from image", "multipart file=@code.png"),
            Endpoint("GET", "/v1/barcode", "Generate barcode", "?text=978020137962&symbology=ean13"),
        ],
    )
)
