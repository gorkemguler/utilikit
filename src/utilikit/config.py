"""Runtime configuration (env vars prefixed ``UTILIKIT_``; ``.env`` auto-loaded)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="UTILIKIT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -- server ------------------------------------------------------------
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8400)
    log_level: str = Field(default="INFO")
    data_dir: Path = Field(default=Path("./var"))
    public_base_url: str = Field(default="", description="For building absolute links (shortener).")

    # -- auth -----------------------------------------------------------
    # Comma-separated API keys. Empty => the API is open (fine on a trusted LAN).
    api_keys: str = Field(default="")
    # Paths that never require a key even when keys are set.
    open_paths: str = Field(default="/,/healthz,/metrics,/docs,/redoc,/openapi.json,/static")

    # -- rate limiting (in-process token bucket, per key or per client IP) --
    rate_limit_per_min: int = Field(default=120)
    rate_limit_burst: int = Field(default=40)

    # -- outbound fetch / SSRF guard ----------------------------------
    allow_private_fetch: bool = Field(
        default=False,
        description="Allow tools to fetch RFC1918/loopback/link-local targets. Keep false if exposed.",
    )
    fetch_timeout_seconds: float = Field(default=15.0)
    fetch_max_bytes: int = Field(default=8_000_000)
    fetch_max_redirects: int = Field(default=5)
    fetch_user_agent: str = Field(default="Utilikit/0.1 (+https://github.com/gorkemguler/utilikit)")
    fetch_allow_hosts: str = Field(default="", description="If set, ONLY these host suffixes may be fetched.")
    fetch_deny_hosts: str = Field(default="", description="Extra host suffixes to always refuse.")

    # -- headless browser (screenshot / pdf / render) --------------------
    browser_enabled: bool = Field(default=True, description="Set false to hard-disable capture tools.")
    browser_concurrency: int = Field(default=1, description="Parallel Chromium contexts (RAM!).")
    browser_timeout_seconds: float = Field(default=30.0)
    browser_nav_timeout_seconds: float = Field(default=20.0)

    # -- caching / jobs ------------------------------------------------
    cache_ttl_seconds: int = Field(default=300)
    cache_max_entries: int = Field(default=512)
    job_ttl_seconds: int = Field(default=900)

    # -- request bin / shortener --------------------------------------
    bin_max_requests: int = Field(default=50, description="Requests kept per bin id.")
    shortener_enabled: bool = Field(default=True)

    # -- optional offline IP geolocation ----------------------------
    geoip_mmdb_path: Path = Field(default=Path("./data/GeoLite2-City.mmdb"))

    @field_validator("log_level")
    @classmethod
    def _log(cls, v: str) -> str:
        v = v.upper()
        if v not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("invalid log level")
        return v

    @property
    def keys(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}

    @property
    def open_path_list(self) -> list[str]:
        return [p.strip() for p in self.open_paths.split(",") if p.strip()]

    @property
    def db_path(self) -> Path:
        return self.data_dir / "utilikit.db"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s
