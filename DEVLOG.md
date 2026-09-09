### 07.09.2026



### 08.09.2026

### 09.09.2026
- nginx kaldırıldı → Caddy; `Caddyfile` ana dizinde (statik serve + `/api` proxy). `web` tek seferlik build servisi (`web-static` volume), `caddy` 8080'de. Doğrulandı.
- Local dev: `scripts/dev.sh` (uvicorn `--reload` + Vite HMR, Docker'sız) + opsiyonel `docker-compose.dev.yml`; README.md eklendi
- Frontend UI: Gemini tarzı ana sayfa (daisyUI, özel gemlight/gemdark temalar). Header, Welcome (öneri karoları), MessageList (markdown-lite + kaynak/guard çipleri), Composer (dosya ekleme + otomatik büyüyen giriş). `/api/qa` stub'ı `src/lib/chat.js`'te. Build + SSR + headless-chrome ile doğrulandı
- **Basit RAG** (web-api): `.env` (gitignore'lu, anahtarlar boş), Nemotron 3 Ultra streaming + Nemotron 3 Embed 1B; fazlar `extracting→chunking→embedding→done`; numpy+`.ragdata` vektör saklama; uçlar `POST /api/documents` (SSE), `GET/DELETE /api/documents`, `POST /api/qa` (SSE). Sahte modelle uçtan uca + restart kalıcılığı doğrulandı; ön yüz gerçek API'ye bağlandı (`lib/api.js`)
- Orijinal dosyalar depoda: `.ragdata/files/<doc_id>/<ad>`; chunk'lar depodaki kopyadan; `storing` fazı (UI loading) + `GET /api/documents/{id}/file` indirme
- **Workspace mimarisi**: sohbet=workspace; Postgres (`db` servisi) + SQLModel (workspaces/documents/chat_messages/embeddings, enum+migration'sız create_all); vektörler ChromaDB (`chroma_data/`, workspace-scope'lu); dosyalar `storage/<doc_id>/`; stream'li upload + XHR percent progress + çift aşamalı iptal; auto-title (ilk 60 karakter); restart stale→failed. Fake model e2e doğrulandı

### 10.09.2026

### 11.09.2026

### 12.09.2026

### 13.09.2026

### 14.09.2026

