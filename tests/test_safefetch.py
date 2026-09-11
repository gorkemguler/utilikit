"""SSRF guard + stateful tools (bin, shortener) + a browser-disabled check."""

import pytest

from utilikit.safefetch import BlockedTarget, assert_host_allowed


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "10.1.2.3", "192.168.0.5", "169.254.169.254", "foo.local"])
def test_private_and_meta_hosts_blocked(host):
    with pytest.raises(BlockedTarget):
        assert_host_allowed(host)


def test_public_host_ok():
    addrs = assert_host_allowed("1.1.1.1")
    assert addrs == ["1.1.1.1"]


def test_allow_private_opt_in(monkeypatch):
    from utilikit import config

    monkeypatch.setenv("UTILIKIT_ALLOW_PRIVATE_FETCH", "true")
    config.get_settings.cache_clear()
    try:
        assert assert_host_allowed("127.0.0.1") == ["127.0.0.1"]
    finally:
        config.get_settings.cache_clear()


def test_screenshot_disabled_returns_503(client):
    r = client.get("/v1/screenshot", params={"url": "https://example.com"})
    assert r.status_code == 503
    assert r.json()["error"]["type"] == "feature_unavailable"


def test_headers_tool_blocks_internal_url(client):
    r = client.get("/v1/http/headers", params={"url": "http://169.254.169.254/latest/meta-data/"})
    assert r.status_code == 400
    assert r.json()["error"]["type"] == "blocked_target"


def test_request_bin_capture_and_list(client):
    bid = client.get("/v1/bin/new").json()["bin_id"]
    client.post(f"/bin/{bid}?foo=1", json={"hello": "world"})
    client.get(f"/bin/{bid}")
    listing = client.get(f"/v1/bin/{bid}").json()
    assert listing["count"] == 2
    assert listing["requests"][0]["method"] == "GET"
    assert "world" in listing["requests"][1]["body"]
    assert listing["requests"][1]["method"] == "POST"


def test_shortener_create_and_redirect(client):
    made = client.post("/v1/short", json={"url": "https://example.com/some/very/long/path", "code": "demo1"}).json()
    assert made["code"] == "demo1"
    r = client.get("/s/demo1", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "https://example.com/some/very/long/path"
    assert client.get("/v1/short/demo1").json()["hits"] == 1


def test_shortener_rejects_internal_target(client):
    r = client.post("/v1/short", json={"url": "http://10.0.0.1/admin"})
    assert r.status_code == 400
