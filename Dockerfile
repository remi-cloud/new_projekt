# Single-container image for Render (SPA + API on $PORT).
# Mac / Hetzner: use docker compose (separate frontend and backend images).
# Multi-arch: node and python base images publish linux/amd64 and linux/arm64.
# Secrets stay out of this image — pass them at runtime.

FROM node:22-alpine AS frontend-build

WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM python:3.12-slim AS python-build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libc6-dev \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080 \
    CYCLICAL_DATABASE_PATH=/data/db/trader.db \
    CYCLICAL_PORTFOLIO_DATABASE_PATH=/data/portfolio/portfolio.db \
    CYCLICAL_PORTFOLIO_RESTORE_BACKUP=false \
    CYCLICAL_SOCIAL_AUTO_POST=true \
    CYCLICAL_SOCIAL_DRY_RUN=true \
    CYCLICAL_BINANCE_AI_BOT_DRY_RUN=true

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        gosu \
        libffi8 \
        libssl3 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin app \
    && mkdir -p /data/db /data/portfolio /app/data/news_images /backups \
    && chown -R app:app /data /app /backups

COPY --from=python-build /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app backend/ /app/
COPY --from=frontend-build --chown=app:app /src/dist /app/static
RUN chmod 755 /app/start.sh /app/docker-entrypoint.sh \
    && python -c "import curl_cffi, fastapi, PIL, uvicorn"

# Entrypoint starts as root only to open the shared portfolio folder, then
# execs the server as uid 10001.
EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
    CMD gosu app python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('PORT','8080'), timeout=4)"

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["/app/start.sh"]
