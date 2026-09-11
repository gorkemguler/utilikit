# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning aims to follow [SemVer](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-09-10

### Added
- FastAPI app with a plugin-style tool registry, HTML tool index at `/`,
  machine-readable catalogue at `GET /v1/tools`, `/healthz`, `/metrics`.
- **Network & OSINT**: `whois/domain` (RDAP + port-43 fallback), `whois/ip`,
  `asn` (Team Cymru), `ip/info` (RDAP + rDNS + ASN + optional geo),
  `dns/records`, `dns/reverse`, `dns/propagation`, `http/headers`
  (+ security-header audit), `http/redirects`, `tls/cert`, `net/tcp-ping`,
  `net/port-check`.
- **Web capture** (optional `browser` extra): `screenshot`, `pdf`, `render`,
  with a sync or async-job mode.
- **Web helpers**: `unfurl`, `readability`, `links`, `html2text`, `favicon`,
  `ua/parse`, `mime`, `luhn`, a webhook **request bin**, a **URL shortener**.
- **Media**: `image/transform`, `image/thumbnail`, `image/exif`,
  `image/strip-exif`, `image/palette`, `og-image` (browserless), `qr`,
  `qr/decode` (optional `decode` extra), `barcode`.
- **Codecs & crypto**: `encode`/`decode`, multi-algorithm `hash`, `hmac`,
  `jwt/decode`.
- **Generators**: `id/uuid` (v1/v4/v7), `id/ulid`, `id/nanoid`, `password`,
  `passphrase`, `password/strength`.
- **Text & data**: `slugify`, `case`, `lorem`, `diff`, `markdown`,
  `text/stats`, `regex/test`, `json/format`, `json/query`, `convert/yaml-json`,
  `convert/csv-json`, `base/convert`.
- **Time & colour**: `time/now`, `time/convert`, `cron/next`,
  `duration/humanize`, `color/convert`, `color/contrast`, `color/palette`.
- SSRF guard (`safefetch`), token-bucket rate limiting, optional API-key auth,
  TTL cache, in-memory job store.
- Deploy: Dockerfile (+ browser), `docker compose`, systemd unit, install
  script, Ansible role. CI: ruff + pytest on 3.11 / 3.12 + multi-arch image.
- 55 tests passing; ruff clean.

[Unreleased]: https://github.com/gorkemguler/utilikit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/gorkemguler/utilikit/releases/tag/v0.1.0
