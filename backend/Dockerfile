# API image. Build context: backend/
# Multi-arch: python:3.12-slim publishes linux/amd64 and linux/arm64.

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libc6-dev \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000 \
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

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app . .
RUN chmod 755 /app/start.sh /app/docker-entrypoint.sh \
    && python -c "import curl_cffi, fastapi, PIL, uvicorn"

# Entrypoint starts as root only to open the shared portfolio folder, then
# execs the server as uid 10001. Do not leave USER app above that step.
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
    CMD gosu app python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('PORT','8000'), timeout=4)"

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["/app/start.sh"]
