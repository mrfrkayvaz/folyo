# Folyo — Belge Analiz & Soru-Cevap Sistemi

PDF / JPG / PNG belge yükle, belge hakkında doğal dilde soru sor; yanıtlar **kaynak gösterimiyle** ve hallucination guard'ı ile döner (case_study MVP).

Mimari kararların gerekçeleri: [`arch.md`](arch.md). Geliştirme günlüğü: [`DEVLOG.md`](DEVLOG.md).

## Mimari (canlı geliştirme stack'i — brüv modeli)

| Servis | Rol | Port (host) |
|---|---|---|
| `web` | Vite dev server + **HMR** (kaynak bind-mount) | **5173** |
| `web-api` | FastAPI / uvicorn `--reload` (kaynak bind-mount) | 8000 (debug) |
| `caddy` | Opsiyonel ters proxy (`Caddyfile` ana dizinde) | **8080** |
| `db` | Postgres | 5432 |

```
Tarayıcı → :5173 (Vite HMR) ─ /api → vite proxy ─→ web-api:8000
Tarayıcı → :8080 (Caddy) ─┬─ /api/* → web-api:8000
                          └─ geri kalan → web:5173 (Vite dev)
```

Kaynak kod bind-mount'ludur: **kod düzenle → anında yansır** (frontend HMR, backend `--reload`). Build gerekmez.

## Geliştirme — her şey Docker'da, anında güncelleme

```bash
docker compose up -d --build        # → http://localhost:5173 (HMR) · :8080 (Caddy)
```

- **Frontend:** http://localhost:5173 — Vite **HMR**: dosyayı kaydet → tarayıcı anında güncellenir, **build gerekmez**.
- **Backend:** http://localhost:8000 — uvicorn `--reload`: `.py` kaydet → otomatik restart.
- `/api` istekleri `:5173`'te `vite.config.js` proxy'si ile, `:8080`'de Caddy ile 8000'e gider (CORS derdi yok).

Bakım komutları:

```bash
docker compose up -d --build web        # yeni npm paketi (imaj katmanı)
docker compose build web-api            # yeni Python paketi (uv sync)
docker compose up -d --force-recreate web-api   # .env değişince
```

Alternatif — Docker'sız, host'ta (iki terminal; `scripts/dev.sh` de var):

```bash
# Terminal 1 — backend
cd web-api && uv run uvicorn app.main:app --reload --port 8000
# Terminal 2 — frontend
cd web && npm run dev
```

## Klasörler

```
Caddyfile            ← caddy servis yapılandırması (:8080 → web + web-api proxy)
docker-compose.yml   ← canlı dev stack: db + web-api + web + caddy
web/                 ← React + Vite + Tailwind + daisyUI (Dockerfile.dev → dev imajı)
web-api/             ← FastAPI + uv
scripts/dev.sh       ← Docker'sız local dev (host'ta)
```

## RAG & API — kurulum

```bash
cp web-api/.env.example web-api/.env   # sonra .env'yi düzenle
# .env içinde doldur:
#   LLM_API_KEY   → sağlayıcı API anahtarı
#   LLM_BASE_URL  → OpenAI uyumlu taban adres (örn: https://api.saglayici.com/v1)
# Modeller (ücretsiz OpenRouter varyantları) .env'den gelir, kodda varsayılan yok.
# DB: db servisi icin once `docker compose up -d db` 
```

### API uçları (workspace'li)

- `POST /api/workspaces` — yeni sohbet (workspace) · `GET /api/workspaces` · `GET/DELETE /api/workspaces/{id}`
- `POST /api/workspaces/{id}/documents` — belge yükle (stream; seçer seçmez başlar, iptal destekli)
- `GET /api/documents/{id}` · `POST /api/documents/{id}/cancel` · `DELETE /api/documents/{id}` · `GET /api/documents/{id}/file`
- `POST /api/workspaces/{id}/qa` — soru sor; SSE: `meta{sources} → delta* → done` (mesajlar kaydedilir)
- `GET /api/health`

Saklama: **Postgres** (`db` servisi → workspaces/documents/chat_messages/embeddings) + **ChromaDB** (`web-api/chroma_data/`) + orijinal dosyalar (`web-api/storage/<doc_id>/`). Görsel/OCR desteği arch.md §3.3 kararı bekliyor — şimdilik PDF (metin katmanı), TXT, MD yükleyebilirsin.
