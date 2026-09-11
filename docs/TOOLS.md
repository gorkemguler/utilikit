# Tool catalogue

*[Türkçe için buraya bakabilirsin](TOOLS.tr.md).*

Auto-generated from the registry. Interactive docs live at `/docs`; a
machine-readable version at `GET /v1/tools`.

**14 tools · 68 endpoints · 8 categories**


## Codecs & crypto

### Encoding, hashing & JWT

base64/32/hex/url/html/ascii85 encode + decode, multi-algorithm hashing, HMAC, JWT decode (no verify).

| Method | Path | What | Example |
|---|---|---|---|
| `POST` | `/v1/encode` | Encode text | `{"text":"hello","encoding":"base64"}` |
| `POST` | `/v1/decode` | Decode text | `{"text":"aGVsbG8=","encoding":"base64"}` |
| `POST` | `/v1/hash` | Hash with many algorithms | `{"text":"hello","algorithms":["sha256","blake2b"]}` |
| `POST` | `/v1/hmac` | HMAC sign | `{"message":"m","key":"k","algorithm":"sha256"}` |
| `GET` | `/v1/jwt/decode` | Decode a JWT | `?token=eyJ...` |


## Generators

### IDs & passwords

UUID v1/v4/v7, ULID, Nano ID, random passwords & passphrases, strength estimate.

| Method | Path | What | Example |
|---|---|---|---|
| `GET` | `/v1/id/uuid` | UUIDs | `?version=7&count=3` |
| `GET` | `/v1/id/ulid` | ULIDs | `?count=3` |
| `POST` | `/v1/id/nanoid` | Nano IDs | `{"size":12}` |
| `GET` | `/v1/password` | Random password | `?length=24&symbols=true` |
| `GET` | `/v1/passphrase` | Passphrase | `?words=5` |
| `GET` | `/v1/password/strength` | Strength check | `?password=hunter2` |


## Media

### Image processing

Resize/convert/re-compress, square thumbnails, read & strip EXIF, colour palette, and a browserless OpenGraph card generator.

| Method | Path | What | Example |
|---|---|---|---|
| `POST` | `/v1/image/transform` | Resize/convert | `?url=...&width=800&format=webp` |
| `POST` | `/v1/image/thumbnail` | Square thumbnail | `?url=...&size=256` |
| `POST` | `/v1/image/exif` | Read EXIF | `multipart file=@photo.jpg` |
| `POST` | `/v1/image/strip-exif` | Strip metadata | `multipart file=@photo.jpg` |
| `POST` | `/v1/image/palette` | Dominant colours | `?url=...` |
| `GET` | `/v1/og-image` | Social card PNG | `?title=Hello&subtitle=World&theme=blue` |

### QR & barcodes  _(needs: decode (for /v1/qr/decode))_

Generate QR codes (PNG/SVG) and 1-D barcodes; decode QR/barcodes from an image (optional extra).

| Method | Path | What | Example |
|---|---|---|---|
| `GET` | `/v1/qr` | Generate QR | `?text=https://example.com&format=svg` |
| `POST` | `/v1/qr/decode` | Decode from image | `multipart file=@code.png` |
| `GET` | `/v1/barcode` | Generate barcode | `?text=978020137962&symbology=ean13` |


## Network & OSINT

### DNS lookups

Resolve any record type, reverse DNS, and a propagation check across 5 public resolvers.

| Method | Path | What | Example |
|---|---|---|---|
| `GET` | `/v1/dns/records` | Records for a name | `?name=example.com&types=A,MX,TXT` |
| `GET` | `/v1/dns/reverse` | PTR for an IP | `?ip=1.1.1.1` |
| `GET` | `/v1/dns/propagation` | Compare resolvers | `?name=example.com&type=A` |

### HTTP & TLS inspection

Headers + security-header audit, redirect-chain trace, TLS certificate inspector, TCP ping and port check. All SSRF-guarded.

| Method | Path | What | Example |
|---|---|---|---|
| `GET` | `/v1/http/headers` | Headers + timing | `?url=https://example.com` |
| `GET` | `/v1/http/redirects` | Redirect chain | `?url=http://google.com` |
| `GET` | `/v1/tls/cert` | TLS certificate | `?host=example.com` |
| `GET` | `/v1/net/tcp-ping` | TCP connect latency | `?host=1.1.1.1&port=443` |
| `GET` | `/v1/net/port-check` | Port scan (tiny) | `?host=example.com&ports=22,80,443` |

### WHOIS / RDAP / ASN  _(needs: geo (optional, for /v1/ip/info geo))_

Domain & IP registration data via RDAP (port-43 fallback for ccTLDs), origin-ASN, and a combined IP dossier with optional offline geolocation.

| Method | Path | What | Example |
|---|---|---|---|
| `GET` | `/v1/whois/domain` | Domain WHOIS | `?domain=example.com` |
| `GET` | `/v1/whois/ip` | IP WHOIS | `?ip=1.1.1.1` |
| `GET` | `/v1/asn` | Origin ASN | `?ip=8.8.8.8` |
| `GET` | `/v1/ip/info` | Full IP dossier | `?ip=8.8.8.8` |


## Text & data

### JSON / YAML / CSV

JSON pretty/minify/validate, JSONPath queries, YAML↔JSON, CSV↔JSON, integer base conversion.

| Method | Path | What | Example |
|---|---|---|---|
| `POST` | `/v1/json/format` | Format JSON | `{"data":"{\"a\":1}"}` |
| `POST` | `/v1/json/query` | JSONPath | `{"data":"{\"a\":[1,2]}","path":"$.a[*]"}` |
| `POST` | `/v1/convert/yaml-json` | YAML↔JSON | `{"data":"a: 1","direction":"yaml2json"}` |
| `POST` | `/v1/convert/csv-json` | CSV↔JSON | `{"data":"a,b\n1,2","direction":"csv2json"}` |
| `GET` | `/v1/base/convert` | Base convert | `?value=255&from_base=10&to_base=16` |

### Text utilities

slugify, case conversion, lorem ipsum, unified diff, Markdown→HTML, text stats, regex tester.

| Method | Path | What | Example |
|---|---|---|---|
| `GET` | `/v1/slugify` | URL slug | `?text=Merhaba Dünya!` |
| `GET` | `/v1/case` | Convert case | `?text=helloWorld&to=kebab` |
| `GET` | `/v1/lorem` | Placeholder text | `?paragraphs=2` |
| `POST` | `/v1/diff` | Unified diff | `{"a":"foo\n","b":"bar\n"}` |
| `POST` | `/v1/markdown` | Markdown to HTML | `{"text":"# Hi **there**"}` |
| `GET` | `/v1/text/stats` | Text stats | `?text=the quick brown fox` |
| `GET` | `/v1/regex/test` | Regex tester | `?pattern=\d+&text=a1b22` |


## Time & colour

### Colour tools

Convert between hex/rgb/hsl/hsv, WCAG contrast ratios, random harmonious palettes.

| Method | Path | What | Example |
|---|---|---|---|
| `GET` | `/v1/color/convert` | Convert colour | `?color=%233b82f6` |
| `GET` | `/v1/color/contrast` | Contrast ratio | `?foreground=%23fff&background=%23555` |
| `GET` | `/v1/color/palette` | Random palette | `?count=5&scheme=analogous` |

### Time & scheduling

Now in many timezones, timestamp parsing/conversion, cron next-runs, duration humanising.

| Method | Path | What | Example |
|---|---|---|---|
| `GET` | `/v1/time/now` | Current time | `?timezones=Europe/Istanbul,UTC` |
| `GET` | `/v1/time/convert` | Convert timestamp | `?value=1700000000&to_timezone=Europe/Istanbul` |
| `GET` | `/v1/cron/next` | Cron next runs | `?expression=*/15 * * * *&count=3` |
| `GET` | `/v1/duration/humanize` | Humanize seconds | `?seconds=93784` |


## Web capture

### Screenshots & PDF  _(needs: browser)_

Full/viewport screenshots (PNG/JPEG), URL to PDF, and raw-HTML render. Sync or async (job) mode. Needs the 'browser' extra.

| Method | Path | What | Example |
|---|---|---|---|
| `GET` | `/v1/screenshot` | Screenshot a URL | `?url=https://example.com&full_page=true&dark=true` |
| `GET` | `/v1/pdf` | URL to PDF | `?url=https://example.com&paper=A4` |
| `POST` | `/v1/render` | Render raw HTML | `{"html":"<h1>hi</h1>","as_pdf":true}` |
| `GET` | `/v1/jobs/{id}/result` | Async job binary | `` |


## Web helpers

### Page metadata & extraction

Unfurl a URL (OG/Twitter/oEmbed/favicon/canonical), pull the main article text, list & classify links, HTML to text. SSRF-guarded.

| Method | Path | What | Example |
|---|---|---|---|
| `GET` | `/v1/unfurl` | Link preview data | `?url=https://github.com` |
| `GET` | `/v1/readability` | Main article text | `?url=https://example.com/post&as_markdown=true` |
| `GET` | `/v1/links` | Extract links | `?url=https://example.com` |
| `GET` | `/v1/html2text` | HTML to text | `?url=https://example.com` |
| `GET` | `/v1/favicon` | Best favicon URL | `?url=https://github.com` |

### Web helpers, request bin & shortener

User-agent parser, MIME guess, Luhn check, a webhook request bin, and a URL shortener (SQLite-backed).

| Method | Path | What | Example |
|---|---|---|---|
| `GET` | `/v1/ua/parse` | Parse a UA string | `?user_agent=Mozilla/5.0 ... Chrome/125` |
| `GET` | `/v1/mime` | Guess MIME type | `?filename=archive.tar.gz` |
| `GET` | `/v1/luhn` | Luhn checksum | `?number=4242424242424242` |
| `GET` | `/v1/bin/new` | New request bin | `` |
| `ANY` | `/bin/{id}` | Capture a request (public) | `point a webhook here` |
| `GET` | `/v1/bin/{id}` | List captured requests | `` |
| `POST` | `/v1/short` | Create short link | `{"url":"https://example.com/very/long"}` |
| `GET` | `/s/{code}` | Redirect (public) | `` |

