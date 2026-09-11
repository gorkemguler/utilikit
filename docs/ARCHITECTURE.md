# Architecture

## One process, many small tools

```
                         ┌──────────────────────────── FastAPI app ───────────────┐
 HTTP ──► RateLimitMiddleware ──► router (per tool) ──► handler ──► JSON / bytes   │
          (token bucket,          [Depends(require_key)]     │                      │
           per key or IP)                                    ├─ safefetch (SSRF)   │
          + metrics counters                                 ├─ cache (TTL)        │
                                                             ├─ browser (Playwright)│
                                                             ├─ db (sqlite: bin,   │
                                                             │      shortener)     │
                                                             └─ jobs (async store) │
                         └───────────────────────────────────────────────────────┘
```

* **`app.py`** builds the app: installs error handlers, adds the rate-limit
  middleware, imports `utilikit.tools` (which registers every router), mounts
  each router under `Depends(require_key)`, and adds the meta routes
  (`/`, `/healthz`, `/metrics`, `/v1/tools`, `/v1/jobs/{id}`).
* **`registry.py`** - `register(ToolInfo(...))` appends to a module-level list.
  Routers are ordinary `APIRouter`s (full OpenAPI, validation, docs); the
  `ToolInfo` metadata only drives the HTML index and `GET /v1/tools`.
* A `ToolInfo` may carry a `public_router` for routes that must work **without**
  an API key - the request-bin capture (`/bin/{id}`) and shortener redirect
  (`/s/{code}`), which external callers hit without your key.

## Cross-cutting modules

| Module | Responsibility |
|---|---|
| `config.py` | `Settings` (pydantic-settings), `UTILIKIT_*` env, `.env` |
| `errors.py` | `ToolError` / `UpstreamError` / `FeatureUnavailable` + handlers → `{"error": {...}}` |
| `security.py` | `require_key` dependency; `REQUESTS` / `TOOL_HITS` counters |
| `ratelimit.py` | ASGI middleware: token bucket per `key:` / `ip:` identity; sets metrics |
| `safefetch.py` | `assert_host_allowed()` (DNS + private/meta IP refusal) and `fetch()` (manual redirects, size/time caps). **Every URL-fetching tool uses this.** |
| `cache.py` | `TTLCache` + `@cached(ttl=…)` for expensive sync calls (whois, tls, dns) |
| `browser.py` | lazy Playwright/Chromium; `FeatureUnavailable` if absent; `Semaphore` |
| `jobs.py` | in-memory `JobStore` for async screenshot/pdf; TTL-pruned |
| `db.py` | raw `sqlite3` for the two stateful tools only |

## Request flow for a URL tool (e.g. `/v1/unfurl`)

1. middleware: rate-limit check, increment `TOOL_HITS["v1/unfurl"]`.
2. `require_key` dependency (no-op if `UTILIKIT_API_KEYS` is empty).
3. handler calls `safefetch.fetch(url)`:
   * scheme check → resolve host → refuse private/meta IPs → GET with capped
     redirects/bytes/time → re-check each hop.
4. parse with BeautifulSoup, return JSON.
5. middleware: increment `REQUESTS["2xx"]`.

## Adding a tool

One file in `src/utilikit/tools/`, add its name to `_MODULES` in
`tools/__init__.py`, add a test. A new tool that fetches a URL should go
through `utilikit.safefetch`; keep heavy optional dependencies behind a
function-local import and a `FeatureUnavailable` fallback.

## Why these choices

* **Single process, no broker** - a toolbox on a Pi should be one `pip install`
  and one service. Async jobs use `asyncio.create_task`, not Celery.
* **SQLite only for the two things that need persistence** - everything else is
  a pure function of its inputs.
* **Playwright optional** - the core image/pip install stays small; screenshots
  are opt-in.
* **Registry is metadata, routers are vanilla FastAPI** - you keep first-class
  OpenAPI docs and get a generated index page for free.
