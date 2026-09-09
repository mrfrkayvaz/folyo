#!/usr/bin/env bash
# Folyo — local geliştirme (Docker/Caddy OLMAZ, anında hot-reload)
# Kullanım: scripts/dev.sh   (Ctrl+C ile ikisi de kapanır)
#
#   Backend  → http://localhost:8000  (uvicorn --reload: kaydet → otomatik restart)
#   Frontend → http://localhost:5173  (Vite HMR: kaydet → tarayıcı anında güncellenir)
#   /api istekleri Vite proxy ile 8000'e gider (vite.config.js) — CORS derdi yok
#
# NOT: Docker tercih edersen build gerekmez: `docker compose up -d --build`
#      (docker-compose.yml canlı dev stack: bind-mount + HMR + --reload)

set -euo pipefail
cd "$(dirname "$0")/.."

cleanup() {
  trap - INT TERM
  kill 0 2>/dev/null || true
}
trap cleanup INT TERM

echo "[dev] backend  : uv run uvicorn app.main:app --reload  → http://localhost:8000"
echo "[dev] frontend : npm run dev (HMR)                    → http://localhost:5173"
echo "[dev] Ctrl+C ile ikisi de durur."

(cd web-api && exec uv run uvicorn app.main:app --reload --port 8000) &
(cd web && exec npm run dev) &

wait
