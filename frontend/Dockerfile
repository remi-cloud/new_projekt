# SPA image. Build context: frontend/
# Multi-arch: node and nginx-unprivileged publish linux/amd64 and linux/arm64.

FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine

USER root
RUN apk add --no-cache curl
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
# nginx -t as root leaves /tmp/nginx.pid owned by root; the sticky /tmp then
# blocks the nginx user from replacing that pid file.
RUN chown -R nginx:nginx /usr/share/nginx/html /etc/nginx/conf.d/default.conf /var/log/nginx \
    && rm -f /tmp/nginx.pid
USER nginx
RUN nginx -t

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
    CMD curl -fsS http://127.0.0.1:8080/healthz >/dev/null || exit 1
