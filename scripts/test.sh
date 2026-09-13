#!/usr/bin/env bash
# Tüm atomik test suite'lerini çalıştırır (her servis kendi venv'inde).
# Ön koşul: web-api/panel-api/worker'da `uv sync` (pytest dev-grubuna eklendi).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "===== SUITE 1: shared + web-api ====="
(cd "$ROOT/web-api" && uv run --no-sync pytest ../tests -q)

echo
echo "===== SUITE 2: panel-api ====="
(cd "$ROOT/panel-api" && uv run --no-sync pytest tests -q)

echo
echo "===== SUITE 3: worker (extract.blocks) ====="
(cd "$ROOT/worker" && uv run --no-sync pytest tests -q)

echo
echo "===== SUITE 4: web (React) ====="
(cd "$ROOT/web" && npm run test)

echo
echo "===== SUITE 5: panel (React) ====="
(cd "$ROOT/panel" && npm run test)

echo
echo "Tüm suite'ler geçti."