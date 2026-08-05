# Multi-stage: build frontend WWW + backend API in one image
# Run: docker compose up --build -d  →  http://localhost:8080

# Stage 1: Build React SPA
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
# Need devDependencies (vite, typescript) to build the SPA
RUN npm ci || npm install
COPY frontend/ .
RUN npm run build

# Stage 2: Python backend + static WWW
FROM python:3.12-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    CYCLICAL_DATABASE_PATH=/app/data/trader.db \
    CYCLICAL_PORTFOLIO_DATABASE_PATH=/app/data/baza_portfela/portfolio.db \
    CYCLICAL_PORTFOLIO_RESTORE_BACKUP=false

RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY --from=frontend-build /app/frontend/dist ./static

RUN mkdir -p data/baza_portfela \
    && chmod +x /app/start.sh

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=8s --start-period=40s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=5)"

CMD ["/app/start.sh"]
