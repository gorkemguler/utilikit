"""Fast, deterministic tests for the offline tools."""

import base64

import pytest


# ------------------------------------------------------------------ codec
def test_encode_decode_roundtrip(client):
    enc = client.post("/v1/encode", json={"text": "héllo", "encoding": "base64"}).json()
    assert enc["result"] == base64.b64encode("héllo".encode()).decode()
    back = client.post("/v1/decode", json={"text": enc["result"], "encoding": "base64"}).json()
    assert back["text"] == "héllo"


def test_hash_multi(client):
    r = client.post("/v1/hash", json={"text": "hello", "algorithms": ["sha256", "crc32", "blake2b"]}).json()
    assert r["hashes"]["sha256"] == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    assert r["hashes"]["crc32"] == "3610a686"
    assert len(r["hashes"]["blake2b"]) == 128


def test_hash_rejects_unknown_algo(client):
    r = client.post("/v1/hash", json={"text": "x", "algorithms": ["sha999"]})
    assert r.status_code == 400 and r.json()["error"]["type"] == "tool_error"


def test_jwt_decode(client):
    tok = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjMiLCJuYW1lIjoiQWxpY2UiLCJleHAiOjB9.c2ln"
    r = client.get("/v1/jwt/decode", params={"token": tok}).json()
    assert r["payload"]["name"] == "Alice"
    assert r["verified"] is False
    assert any("expired" in w for w in r["warnings"])


# ------------------------------------------------------------------ idgen
def test_uuid_versions(client):
    v4 = client.get("/v1/id/uuid", params={"version": 4, "count": 3}).json()
    assert len(v4["ids"]) == 3 and v4["ids"][0][14] == "4"
    v7 = client.get("/v1/id/uuid", params={"version": 7}).json()
    assert v7["ids"][0][14] == "7"


def test_ulid_is_26_crockford_chars(client):
    ids = client.get("/v1/id/ulid", params={"count": 5}).json()["ids"]
    assert all(len(i) == 26 for i in ids)
    assert all(set(i) <= set("0123456789ABCDEFGHJKMNPQRSTVWXYZ") for i in ids)


def test_password_entropy_reported(client):
    r = client.get("/v1/password", params={"length": 20, "symbols": True}).json()
    assert len(r["passwords"][0]) == 20 and r["entropy_bits"] > 100


# ------------------------------------------------------------------ text
@pytest.mark.parametrize(
    "text,to,expected",
    [
        ("helloWorld", "snake", "hello_world"),
        ("hello world", "kebab", "hello-world"),
        ("hello_world", "camel", "helloWorld"),
        ("foo bar", "constant", "FOO_BAR"),
    ],
)
def test_case_convert(client, text, to, expected):
    assert client.get("/v1/case", params={"text": text, "to": to}).json()["result"] == expected


def test_slugify_unicode(client):
    assert client.get("/v1/slugify", params={"text": "Merhaba Dünya! 2024"}).json()["slug"] == "merhaba-dunya-2024"


def test_diff_and_stats(client):
    d = client.post("/v1/diff", json={"a": "line one\nline two\n", "b": "line one\nline 2\n"}).json()
    assert d["changed"] and "-line two" in d["unified"]
    s = client.get("/v1/text/stats", params={"text": "The quick brown fox jumps."}).json()
    assert s["words"] == 5 and s["sentences"] == 1


def test_regex_test(client):
    r = client.get("/v1/regex/test", params={"pattern": r"(\d+)", "text": "a12 b345"}).json()
    assert r["count"] == 2 and r["matches"][1]["groups"] == ["345"]


# ------------------------------------------------------------------ data_fmt
def test_json_format_and_query(client):
    f = client.post("/v1/json/format", json={"data": '{"b":2,"a":1}', "sort_keys": True}).json()
    assert f["minified"] == '{"a":1,"b":2}'
    q = client.post("/v1/json/query", json={"data": '{"items":[{"n":1},{"n":2}]}', "path": "$.items[*].n"}).json()
    assert q["results"] == [1, 2]


def test_yaml_json_and_base_convert(client):
    y = client.post("/v1/convert/yaml-json", json={"data": "a: 1\nb: [x, y]", "direction": "yaml2json"}).json()
    assert '"a": 1' in y["json"]
    b = client.get("/v1/base/convert", params={"value": "255", "from_base": 10, "to_base": 16}).json()
    assert b["result"] == "ff"


# ------------------------------------------------------------------ time
def test_time_now_and_convert(client):
    n = client.get("/v1/time/now", params={"timezones": "Europe/Istanbul,UTC"}).json()
    assert "Europe/Istanbul" in n["zones"]
    c = client.get("/v1/time/convert", params={"value": "1700000000", "to_timezone": "UTC"}).json()
    assert c["result"]["iso"].startswith("2023-11-14")


def test_cron_next(client):
    r = client.get("/v1/cron/next", params={"expression": "0 0 * * *", "count": 3}).json()
    assert len(r["next"]) == 3 and all("T00:00:00" in x for x in r["next"])


def test_cron_rejects_bad(client):
    assert client.get("/v1/cron/next", params={"expression": "not a cron"}).status_code == 400


# ------------------------------------------------------------------ color
def test_color_convert_and_contrast(client):
    c = client.get("/v1/color/convert", params={"color": "#3b82f6"}).json()
    assert c["rgb_tuple"] == [59, 130, 246]
    k = client.get("/v1/color/contrast", params={"foreground": "#ffffff", "background": "#000000"}).json()
    assert k["ratio"] == 21.0 and k["AAA_normal"] is True


# ------------------------------------------------------------------ misc
def test_luhn_and_mime_and_ua(client):
    assert client.get("/v1/luhn", params={"number": "4242 4242 4242 4242"}).json()["valid"] is True
    assert client.get("/v1/luhn", params={"number": "4242 4242 4242 4243"}).json()["valid"] is False
    assert client.get("/v1/mime", params={"filename": "a.tar.gz"}).json()["mime_type"] == "application/x-tar"
    ua = client.get("/v1/ua/parse", params={"user_agent": "Mozilla/5.0 (X11; Linux) Chrome/125.0 Safari/537"}).json()
    assert ua["browser"] == "Chrome" and ua["os"] == "Linux"
