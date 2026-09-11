# Deployment

Utilikit is one FastAPI process. Pick whichever of these fits.

## Requirements

| | Minimum | Recommended |
|---|---|---|
| Host | Raspberry Pi 3B, or any x86-64 Linux/macOS box | Pi 4B 2 GB / retired laptop |
| RAM | 512 MB (core) | 2 GB (with screenshots) |
| Disk | 2 GB | 4 GB (Chromium ≈ 400 MB) |
| Python | 3.11+ | 3.12 |

Optional extras and their system deps:

| Extra | Enables | Also needs |
|---|---|---|
| `browser` | `screenshot`, `pdf`, `render` | `playwright install --with-deps chromium` |
| `decode` | `qr/decode`, barcode decode | system `libzbar0` (`apt install libzbar0`) |
| `geo` | geolocation in `ip/info` | a `.mmdb` file you supply |

---

## A. Docker (recommended)

```bash
docker run -d --name utilikit -p 8400:8400 \
  -e UTILIKIT_API_KEYS=$(openssl rand -hex 16) \
  -v utilikit-data:/data --shm-size=512m \
  ghcr.io/gorkemguler/utilikit:latest
```

or from a clone: `docker compose up -d --build`.

Lean image without Chromium (smaller, no screenshots):
`docker build --build-arg WITH_BROWSER=0 -t utilikit:lean .`

---

## B. Raspberry Pi / old PC - systemd service

```bash
git clone https://github.com/gorkemguler/utilikit.git && cd utilikit
sudo deploy/scripts/install.sh          # venv at /opt/utilikit, user, unit, env file
sudo $EDITOR /etc/utilikit/utilikit.env # set UTILIKIT_API_KEYS etc.
sudo systemctl enable --now utilikit
curl -s localhost:8400/healthz
```

`install.sh` installs the `browser` + `decode` extras and downloads Chromium by
default; pass `NO_BROWSER=1` to skip (much faster, no screenshots).

Manage it: `systemctl status utilikit`, `journalctl -u utilikit -f`.

---

## C. Ansible (one or more hosts)

```bash
cd deploy/ansible
cp inventory.example.ini inventory.ini    # host(s), api key, options
ansible-playbook -i inventory.ini site.yml
```

---

## D. Bare (dev / trying it out)

```bash
python -m venv .venv && . .venv/bin/activate
pip install "utilikit[browser]"
playwright install --with-deps chromium
utilikit serve
```

---

## Putting it behind a reverse proxy (TLS)

Caddy is the shortest path:

```
tools.example.com {
    reverse_proxy 127.0.0.1:8400
}
```

nginx: proxy `location /` to `http://127.0.0.1:8400;` with
`proxy_set_header X-Forwarded-For $remote_addr;` (Utilikit reads it for
rate-limit identity). Keep the container/service bound to `127.0.0.1` when a
proxy is in front (`UTILIKIT_HOST=127.0.0.1`).

## Hardening when exposed

Set `UTILIKIT_API_KEYS`, keep `UTILIKIT_ALLOW_PRIVATE_FETCH=false`, consider
`UTILIKIT_FETCH_ALLOW_HOSTS`, lower `UTILIKIT_RATE_LIMIT_PER_MIN`, and
terminate TLS at a proxy. See the README's section on exposing this beyond
your LAN for the reasoning behind each of those.

## Resource notes

* Core RSS ~120–180 MB. Each concurrent screenshot adds ~150–250 MB - keep
  `UTILIKIT_BROWSER_CONCURRENCY=1` on 2 GB.
* The SQLite DB (`/data` or `UTILIKIT_DATA_DIR`) only holds request-bin entries
  (capped per bin) and short links - it stays tiny. Still, put it on an SSD or
  add `log2ram` if you care about SD-card wear.
* `utilikit selftest` verifies the install; `GET /metrics` is Prometheus-ready.
