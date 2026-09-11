# Utilikit — self-hostable HTTP toolbox API.
# Multi-arch: linux/amd64 + linux/arm64 (Raspberry Pi 4 / 5).
#
#   docker build -t utilikit .                       # full image (with Chromium)
#   docker build --build-arg WITH_BROWSER=0 -t utilikit:lean .   # no screenshots
FROM python:3.12-slim

ARG WITH_BROWSER=1

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UTILIKIT_DATA_DIR=/data \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# libzbar0 -> optional QR/barcode decode; the rest are wheels' runtime libs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libzbar0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src

RUN if [ "$WITH_BROWSER" = "1" ]; then \
        pip install ".[browser,decode]" && playwright install --with-deps chromium ; \
    else \
        pip install ".[decode]" ; \
    fi

RUN useradd --system --uid 10001 utilikit \
    && mkdir -p /data \
    && chown -R utilikit /data /ms-playwright 2>/dev/null || true
USER utilikit
VOLUME ["/data"]
EXPOSE 8400

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fsS http://localhost:8400/healthz || exit 1

CMD ["utilikit", "serve"]
