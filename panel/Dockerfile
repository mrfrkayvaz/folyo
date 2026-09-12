# Folyo Panel — production (Coolify)
# Vite statik build → Caddy: SPA dosyaları + `/api` → panel-api ters proxy.

# ── Build aşaması: Vite prod build ─────────────────────────────────────────────
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# ── Dağıtım aşaması: Caddy (statik + /api proxy) ───────────────────────────────
FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
# Coolify'da panel-api servis adresine göre ayarla (örn. http://panel-api:8000)
ENV API_UPSTREAM=panel-api:8000
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s CMD wget -qO- http://127.0.0.1/index.html >/dev/null || exit 1