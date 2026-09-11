def test_index_and_health(client):
    r = client.get("/")
    assert r.status_code == 200 and "Utilikit" in r.text

    h = client.get("/healthz").json()
    assert h["status"] == "ok" and h["tools"] >= 12


def test_tools_catalog(client):
    data = client.get("/v1/tools").json()
    assert data["count"] == len(data["tools"])
    paths = {e["path"] for t in data["tools"] for e in t["endpoints"]}
    assert "/v1/whois/domain" in paths
    assert "/v1/screenshot" in paths
    assert "/v1/hash" in paths


def test_metrics_text(client):
    client.get("/healthz")
    client.get("/v1/id/uuid")
    body = client.get("/metrics").text
    assert "utilikit_requests_total" in body
    assert "utilikit_uptime_seconds" in body


def test_unknown_route_is_json_error(client):
    r = client.get("/v1/does-not-exist")
    assert r.status_code == 404
    assert r.json()["error"]["type"] == "http_error"


def test_validation_error_shape(client):
    r = client.get("/v1/slugify")  # missing required ?text=
    assert r.status_code == 422
    assert r.json()["error"]["type"] == "validation_error"


def test_auth_required_when_keys_set(keyed_client):
    assert keyed_client.get("/healthz").status_code == 200  # open
    assert keyed_client.get("/v1/id/uuid").status_code == 401
    ok = keyed_client.get("/v1/id/uuid", headers={"X-API-Key": "secret-key-2"})
    assert ok.status_code == 200
    ok2 = keyed_client.get("/v1/id/uuid?api_key=secret-key-1")
    assert ok2.status_code == 200
    assert keyed_client.get("/v1/id/uuid", headers={"X-API-Key": "nope"}).status_code == 401
