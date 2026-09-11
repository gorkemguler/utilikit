"""Encoders, decoders, hashes, HMAC, JWT inspection."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import html
import json
import urllib.parse
import zlib

from fastapi import APIRouter, Body
from pydantic import BaseModel

from ..errors import ToolError
from ..registry import Endpoint, ToolInfo, register

router = APIRouter(prefix="/v1", tags=["codec"])

_ENCODINGS = {"base64", "base64url", "base32", "base16", "hex", "url", "html", "ascii85"}
_HASHES = [
    "md5",
    "sha1",
    "sha224",
    "sha256",
    "sha384",
    "sha512",
    "sha3_256",
    "sha3_512",
    "blake2b",
    "blake2s",
]


class EncodeIn(BaseModel):
    text: str
    encoding: str = "base64"


class DecodeIn(BaseModel):
    text: str
    encoding: str = "base64"


def _encode(data: bytes, enc: str) -> str:
    if enc == "base64":
        return base64.b64encode(data).decode()
    if enc == "base64url":
        return base64.urlsafe_b64encode(data).decode().rstrip("=")
    if enc == "base32":
        return base64.b32encode(data).decode()
    if enc in {"base16", "hex"}:
        return data.hex()
    if enc == "url":
        return urllib.parse.quote(data.decode("utf-8", "replace"), safe="")
    if enc == "html":
        return html.escape(data.decode("utf-8", "replace"))
    if enc == "ascii85":
        return base64.a85encode(data).decode()
    raise ToolError(f"Unknown encoding {enc!r}. Try one of: {sorted(_ENCODINGS)}")


def _decode(text: str, enc: str) -> bytes:
    try:
        if enc == "base64":
            return base64.b64decode(text + "=" * (-len(text) % 4))
        if enc == "base64url":
            return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
        if enc == "base32":
            return base64.b32decode(text, casefold=True)
        if enc in {"base16", "hex"}:
            return bytes.fromhex(text.strip().replace(" ", "").replace("0x", ""))
        if enc == "url":
            return urllib.parse.unquote_plus(text).encode()
        if enc == "html":
            return html.unescape(text).encode()
        if enc == "ascii85":
            return base64.a85decode(text)
    except (binascii.Error, ValueError) as exc:
        raise ToolError(f"Not valid {enc}: {exc}") from exc
    raise ToolError(f"Unknown encoding {enc!r}.")


@router.post("/encode", summary="Encode text (base64/base64url/base32/hex/url/html/ascii85)")
def encode(body: EncodeIn) -> dict:
    return {"encoding": body.encoding, "result": _encode(body.text.encode("utf-8"), body.encoding)}


@router.post("/decode", summary="Decode text back to UTF-8 (best effort)")
def decode(body: DecodeIn) -> dict:
    raw = _decode(body.text, body.encoding)
    return {
        "encoding": body.encoding,
        "text": raw.decode("utf-8", "replace"),
        "bytes": len(raw),
        "hex": raw.hex(),
    }


@router.post("/hash", summary="Hash text or hex bytes with many algorithms at once")
def hash_text(
    text: str = Body(..., embed=True),
    is_hex: bool = Body(False, embed=True),
    algorithms: list[str] | None = Body(None, embed=True),
) -> dict:
    data = bytes.fromhex(text) if is_hex else text.encode("utf-8")
    algos = algorithms or ["md5", "sha1", "sha256", "sha512"]
    out: dict[str, str] = {}
    for a in algos:
        if a == "crc32":
            out[a] = format(zlib.crc32(data) & 0xFFFFFFFF, "08x")
        elif a in _HASHES:
            out[a] = hashlib.new(a, data).hexdigest()
        else:
            raise ToolError(f"Unknown algorithm {a!r}. Available: {[*_HASHES, 'crc32']}")
    return {"input_bytes": len(data), "hashes": out}


@router.post("/hmac", summary="HMAC of a message with a key")
def hmac_sign(
    message: str = Body(..., embed=True),
    key: str = Body(..., embed=True),
    algorithm: str = Body("sha256", embed=True),
) -> dict:
    if algorithm not in _HASHES:
        raise ToolError(f"Unknown algorithm {algorithm!r}.")
    digest = hmac.new(key.encode(), message.encode(), algorithm)
    return {"algorithm": algorithm, "hex": digest.hexdigest(), "base64": base64.b64encode(digest.digest()).decode()}


@router.get("/jwt/decode", summary="Decode a JWT WITHOUT verifying its signature")
def jwt_decode(token: str) -> dict:
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise ToolError("A JWT has three dot-separated parts.")

    def _seg(s: str) -> dict:
        raw = base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
        return json.loads(raw)

    try:
        header, payload = _seg(parts[0]), _seg(parts[1])
    except (binascii.Error, ValueError, json.JSONDecodeError) as exc:
        raise ToolError(f"Malformed JWT: {exc}") from exc

    import time as _t

    warnings = []
    if "exp" in payload and payload["exp"] < _t.time():
        warnings.append("token is expired (exp in the past)")
    if "nbf" in payload and payload["nbf"] > _t.time():
        warnings.append("token not yet valid (nbf in the future)")
    return {
        "header": header,
        "payload": payload,
        "signature": parts[2],
        "verified": False,
        "warnings": warnings,
    }


register(
    ToolInfo(
        key="codec",
        title="Encoding, hashing & JWT",
        category="Codecs & crypto",
        description=(
            "base64/32/hex/url/html/ascii85 encode + decode, multi-algorithm hashing, HMAC, JWT decode (no verify)."
        ),
        router=router,
        endpoints=[
            Endpoint("POST", "/v1/encode", "Encode text", '{"text":"hello","encoding":"base64"}'),
            Endpoint("POST", "/v1/decode", "Decode text", '{"text":"aGVsbG8=","encoding":"base64"}'),
            Endpoint(
                "POST", "/v1/hash", "Hash with many algorithms", '{"text":"hello","algorithms":["sha256","blake2b"]}'
            ),
            Endpoint("POST", "/v1/hmac", "HMAC sign", '{"message":"m","key":"k","algorithm":"sha256"}'),
            Endpoint("GET", "/v1/jwt/decode", "Decode a JWT", "?token=eyJ..."),
        ],
    )
)
