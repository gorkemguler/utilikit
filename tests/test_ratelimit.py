def test_token_bucket_math(monkeypatch):
    from utilikit import config
    from utilikit.ratelimit import RateLimitMiddleware

    monkeypatch.setenv("UTILIKIT_RATE_LIMIT_PER_MIN", "60")
    monkeypatch.setenv("UTILIKIT_RATE_LIMIT_BURST", "3")
    config.get_settings.cache_clear()
    try:
        mw = RateLimitMiddleware(app=lambda *a: None)
        allowed = [mw._allow("ip:test")[0] for _ in range(5)]
        assert allowed[:3] == [True, True, True]
        assert allowed[3] is False  # burst exhausted, refill is 1/sec
    finally:
        config.get_settings.cache_clear()


def test_429_over_http(monkeypatch):
    from fastapi.testclient import TestClient

    from utilikit import config

    monkeypatch.setenv("UTILIKIT_RATE_LIMIT_PER_MIN", "60")
    monkeypatch.setenv("UTILIKIT_RATE_LIMIT_BURST", "2")
    config.get_settings.cache_clear()
    try:
        from utilikit.app import create_app

        c = TestClient(create_app())
        codes = [c.get("/v1/id/uuid").status_code for _ in range(6)]
        assert 429 in codes
        assert codes[0] == 200
    finally:
        config.get_settings.cache_clear()
