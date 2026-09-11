"""QR + image tools (Pillow only, no network, no browser)."""

import io

from PIL import Image


def test_qr_png_and_svg(client):
    png = client.get("/v1/qr", params={"text": "hello", "format": "png"})
    assert png.status_code == 200 and png.headers["content-type"] == "image/png"
    Image.open(io.BytesIO(png.content)).verify()

    svg = client.get("/v1/qr", params={"text": "hello", "format": "svg"})
    assert svg.headers["content-type"] == "image/svg+xml" and b"<svg" in svg.content


def test_barcode_svg(client):
    r = client.get("/v1/barcode", params={"text": "Utilikit123", "symbology": "code128", "format": "svg"})
    assert r.status_code == 200 and b"<svg" in r.content


def test_og_image_png(client):
    r = client.get("/v1/og-image", params={"title": "Hello World", "subtitle": "from utilikit", "theme": "blue"})
    assert r.status_code == 200
    im = Image.open(io.BytesIO(r.content))
    assert im.size == (1200, 630)


def _tiny_png() -> bytes:
    im = Image.new("RGB", (120, 80), (200, 40, 40))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def test_image_transform_resize(client):
    r = client.post(
        "/v1/image/transform?width=40&format=webp",
        files={"file": ("in.png", _tiny_png(), "image/png")},
    )
    assert r.status_code == 200 and r.headers["content-type"] == "image/webp"
    out = Image.open(io.BytesIO(r.content))
    assert out.width == 40


def test_image_palette(client):
    r = client.post("/v1/image/palette", files={"file": ("in.png", _tiny_png(), "image/png")}).json()
    assert r["colors"][0]["rgb"][0] > 150  # dominant colour is reddish


def test_image_exif_read_empty(client):
    r = client.post("/v1/image/exif", files={"file": ("in.png", _tiny_png(), "image/png")}).json()
    assert r["size"] == [120, 80] and r["has_exif"] is False
