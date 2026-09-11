#!/usr/bin/env bash
# Install Utilikit as a systemd service on this machine (Raspberry Pi OS / Debian / Ubuntu).
#   sudo ./install.sh                 # full install (with Chromium for screenshots)
#   sudo NO_BROWSER=1 ./install.sh    # skip the browser (smaller, faster, no screenshots)
set -euo pipefail

PREFIX="${PREFIX:-/opt/utilikit}"
ETC="${ETC:-/etc/utilikit}"
USER_NAME="${USER_NAME:-utilikit}"
REPO_URL="${REPO_URL:-https://github.com/gorkemguler/utilikit.git}"
REF="${REF:-main}"

log() { printf '\033[1;36m[utilikit]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[utilikit] %s\033[0m\n' "$*" >&2; exit 1; }
[ "$(id -u)" -eq 0 ] || die "run as root (sudo)"
command -v apt-get >/dev/null || die "expects apt (Debian/Ubuntu/Raspberry Pi OS)"

EXTRAS="[decode]"
[ "${NO_BROWSER:-0}" != "1" ] && EXTRAS="[browser,decode]"

log "installing OS packages"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    git python3 python3-venv python3-dev build-essential curl ca-certificates libzbar0

id "$USER_NAME" >/dev/null 2>&1 || {
    log "creating system user $USER_NAME"
    useradd --system --home-dir "$PREFIX" --shell /usr/sbin/nologin "$USER_NAME"
}

mkdir -p "$PREFIX" "$ETC"
install -d -o "$USER_NAME" -g "$USER_NAME" /var/lib/utilikit "$PREFIX/ms-playwright"

if [ -d "$PREFIX/src/.git" ]; then
    log "updating source"
    git -C "$PREFIX/src" fetch --depth 1 origin "$REF" && git -C "$PREFIX/src" reset --hard "origin/$REF"
else
    log "cloning $REPO_URL@$REF"
    git clone --depth 1 --branch "$REF" "$REPO_URL" "$PREFIX/src"
fi

log "building venv (extras: $EXTRAS)"
python3 -m venv "$PREFIX/venv"
"$PREFIX/venv/bin/pip" install -q --upgrade pip
"$PREFIX/venv/bin/pip" install -q "$PREFIX/src$EXTRAS"

if [ "${NO_BROWSER:-0}" != "1" ]; then
    log "downloading Chromium for Playwright (this is the slow part)"
    PLAYWRIGHT_BROWSERS_PATH="$PREFIX/ms-playwright" \
        "$PREFIX/venv/bin/playwright" install --with-deps chromium
    chown -R "$USER_NAME" "$PREFIX/ms-playwright"
fi

if [ ! -f "$ETC/utilikit.env" ]; then
    log "writing starter $ETC/utilikit.env (EDIT IT - at least set UTILIKIT_API_KEYS)"
    KEY="$("$PREFIX/venv/bin/utilikit" gen-key)"
    sed "s|^UTILIKIT_API_KEYS=.*|UTILIKIT_API_KEYS=${KEY}|" "$PREFIX/src/.env.example" > "$ETC/utilikit.env"
    chmod 640 "$ETC/utilikit.env"
    chgrp "$USER_NAME" "$ETC/utilikit.env"
    log "generated API key: ${KEY}"
else
    log "$ETC/utilikit.env already exists, leaving it"
fi

install -m 644 "$PREFIX/src/deploy/systemd/utilikit.service" /etc/systemd/system/utilikit.service
systemctl daemon-reload
systemctl enable --now utilikit.service

sleep 2
log "done. http://$(hostname -I | awk '{print $1}'):8400/"
systemctl --no-pager --lines=5 status utilikit.service || true
