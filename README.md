# Contextus — Belge Analiz & Soru-Cevap Sistemi

PDF / JPG / PNG belge yükle, belge hakkında doğal dilde soru sor; yanıtlar **kaynak gösterimiyle** ve hallucination guard'ı ile döner (case_study MVP).

Mimari kararların gerekçeleri: [`arch.md`](arch.md). Geliştirme günlüğü: [`DEVLOG.md`](DEVLOG.md).

## Mimari

| Servis | Rol | Port (host) |
|---|---|---|
| `caddy` | Ters proxy + SPA statik sunucusu (`Caddyfile` ana dizinde) | **8080** |
| `web` | Frontend build (tek seferlik) → `web-static` volume | — |
| `web-api` | FastAPI / uvicorn backend | 8000 (debug, opsiyonel) |

```
Tarayıcı → :8080 (Caddy) ─┬─ /api/*  → web-api:8000
                          └─ statik   → web-static volume (web servisinin build'i)
```

## Local geliştirme (önerilen — Docker'sız, anında güncelleme)

```bash
scripts/dev.sh
```

- **Frontend:** http://localhost:5173 — Vite **HMR**: dosyayı kaydet → tarayıcı anında güncellenir, **build gerekmez**.
- **Backend:** http://localhost:8000 — uvicorn `--reload`: `.py` kaydet → otomatik restart.
- `/api` istekleri `vite.config.js`'teki proxy ile 8000'e gider (CORS sorunu yok).

Elle de çalıştırabilirsin (iki terminal):

```bash
# Terminal 1 — backend
cd web-api && uv run uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd web && npm run dev
```

> Backend'i host'a kurmak istemiyorsan container'da reload'lu çalıştır:
> `docker compose -f docker-compose.yml -f docker-compose.dev.yml up web-api`
> (frontend yine host'ta `npm run dev`)

## Production (Docker / Caddy)

```bash
docker compose up -d --build        # → http://localhost:8080
```

Kod değişince (sadece production için gereklidir):

```bash
docker compose up -d --build web-api   # backend güncellemesi
docker compose up -d --build web caddy # frontend statik yayını
```

## Klasörler

```
Caddyfile            ← caddy servis yapılandırması (statik + /api proxy)
docker-compose.yml   ← prod: caddy + web + web-api
docker-compose.dev.yml ← dev override (backend container'da reload'lu)
web/                 ← React + Vite + Tailwind + daisyUI
web-api/             ← FastAPI + uv
scripts/dev.sh       ← tek komutla local dev
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
