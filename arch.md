# Arch — Mimari Dokümanı

> Proje: Belge Analiz ve Soru-Cevap Sistemi (case_study.docx)
> Bu dosya mimarinin canlı dokümanıdır. Karar verildikçe güncellenir.

---

## 1. Proje Bağlamı (case_study özeti)

- **Amaç:** Kullanıcının PDF / JPG / PNG belge yükleyip, bu belgeler hakkında doğal dilde soru sorabildiği, yapay zeka destekli Belge Analiz ve Soru-Cevap sistemi.
- **OCR gereksinimi:** Resim belgelerindeki metin okunabilmeli; **Türkçe ve İngilizce** desteklenmeli.
- **Doğruluk:** Sistem belgede olmayan bilgiyi **üretmemeli** (hallucination kontrolü zorunlu).
- **Kullanılabilirlik:** Web arayüzü üzerinden kullanım.
- **Teslimat:** İşlevsel MVP; DEVLOG.md, TESTING.md, demo video, kaynak kod, README.md.
- **Değerlendirme:** Teknik kararların gerekçesi ve alternatif değerlendirmesi önemli — bu doküman o gerekçeleri taşıyacak.

---

## 2. Yüksek Seviye Mimari (hedef)

```
┌──────────┐   yükleme    ┌──────────────┐
│  Web UI  │ ───────────► │  API/Backend │
└──────────┘              └──────┬───────┘
                                │
              ┌─────────────────┼──────────────────┐
              ▼                 ▼                  ▼
       ┌────────────┐    ┌────────────┐    ┌─────────────┐
       │  OCR /     │    │  Embedding │    │  Vector     │
       │  Metin     │    │  Model     │    │  Store      │
       │  Çıkarımı  │    │            │    │             │
       └────────────┘    └────────────┘    └─────────────┘
              │                 │                  ▲
              └────────┬────────┘                  │
                       ▼                           │
              ┌─────────────────┐                  │
              │  Chunking +     │  indexing        │
              │  Preprocessing  │ ─────────────────┘
              └─────────────────┘
                                ┌─────────────────┐
   soru                         │  Retrieval      │
──────────────────────────────► │  (semantic)     │
                                └────────┬────────┘
                                         ▼
                                ┌─────────────────┐      ┌──────────┐
                                │  LLM (RAG)      │ ───► │  Yanıt + │
                                │  + hallucination│      │  Kaynak  │
                                │  guard          │      └──────────┘
                                └─────────────────┘
```

**Temel akış:**
1. Belge yükle → format ayrıştır (PDF metin katmanı + taranmış sayfalar + görseller).
2. Metin çıkar (OCR gerekliyse, TR/EN).
3. Metni normalize et, chunk'la, embed et, vector store'a yaz.
4. Soru gelince → embed → benzer chunk'ları getir → LLM'e bağlam olarak ver → kaynaklarla birlikte yanıt.
5. Hallucination guard'ı aş.

---

## 3. Teknik Yapı (kullanılacak stack)

> Aşağıdaki bölümler **TEKNİK KARAR ALANLARIDIR**. Her kararın altına seçim + gerekçe + değerlendirilen alternatifler yazılır.

### 3.1. Dil / Framework (backend — web-api)
- **Seçim:** Python / FastAPI
- **Gerekçe:** _(doldurulacak — örn: asenkron, tip destekli, AI/ML ekosistemi)_
- **Alternatifler:**_(doldurulacak — örn: Node/Express, Django, Go)_
- **Karar tarihi:** 14.09.2026

**Paket yönetimi:** `uv` (hızlı, lockfile, Python sürüm yönetimi)

### 3.1a. Frontend (web)
- **Seçim:** React + Vite + Tailwind CSS + daisyUI
- **Gerekçe:** _(doldurulacak — örn: hızlı DX, hazır UI bileşenleri, TUI tabanlı hızlı geliştirme)_
- **Alternatifler:** _(doldurulacak — örn: Next.js, Streamlit, Svelte)
- **Karar tarihi:** 14.09.2026

**Klasör konvansiyonu:**
- `web/` → frontend (React + Vite + Tailwind + daisyUI)
- `web-api/` → backend API (FastAPI + uv)

### 3.2. Frontend Detayları (web — React + Vite + Tailwind + daisyUI)
- **Seçim:** React 18 + Vite + Tailwind CSS + daisyUI
- **Gerekçe:** _(doldurulacak)_
- **Alternatifler:** _(doldurulacak)_
- **Karar tarihi:** 14.09.2026
- **Not:** UI bileşenleri için daisyUI kullanılacak (bkz. daisyUI skill).

### 3.3. OCR / Metin Çıkarımı (TR + EN destekli)
- **Seçim:** _(doldurulacak — örn: Tesseract / PaddleOCR / easyOCR / Azure Document Intelligence)_
- **Gerekçe:**
- **Alternatifler:**
- **Karar tarihi:**
- **Not:** TR ve EN dil desteği burada kritik — benchmark/karşılaştırma TESTING.md'ye yansıyacak.

### 3.4. Embedding Modeli
- **Seçim:** NVIDIA Nemotron 3 Embed 1B (free sağlayıcı, OpenAI uyumlu `/embeddings`) — `.env`: `EMBED_MODEL=nvidia/nemotron-3-embed-1b`
- **Gerekçe:** 32K bağlam — 900 karakterlik chunk'lar rahatça sığar; ücretsiz katmanı denemeler için yeterli; nesbenn/ölçüm TESTING.md'de TR+EN ile doğrulanacak
- **Alternatifler:** Llama Nemotron Embed VL 1B V2 (görsel destekli), LFM2.5-Embedding-350M (hızlı ama 512 ctx)
- **Karar tarihi:** 09.09.2026

### 3.5. Vector Store
- **Seçim:** numpy + disk persist (`.ragdata/`: docs.json, chunks.json, vectors.npy) — ekstra servis yok
- **Gerekçe:** Basit RAG MVP'si; tek kullanıcı; bellim/önemsiz veri boyutu; Chroma/Qdrant'a geçiş `store.py` arayüzünde izole
- **Alternatifler:** ChromaDB / Qdrant / pgvector / FAISS
- **Karar tarihi:** 09.09.2026

### 3.6. LLM (soru-cevap / üretim)
- **Seçim:** NVIDIA Nemotron 3 Ultra (free sağlayıcı, OpenAI uyumlu `/chat/completions`, streaming) — `.env`: `LLM_MODEL=nvidia/nemotron-3-ultra`
- **Gerekçe:** 1M bağlam — büyük belgeleri chunk'sız deneme imkânı; streaming 4-5 t/s gerçi yavaş ama ilk token gelene kadar UI "yazıyor…" göstergesi taşır
- **Alternatifler:** İnklikling Small (88 t/s, hızlı iterasyon), Nemotron 3.5 Lightning (1M ctx); model `.env`'den değiştirilebilir — mimariye bağlı değil
- **Karar tarihi:** 09.09.2026

### 3.7. Hallucination Kontrolü / Doğruluk Garantisi
- **Seçim:** _(doldurulacak — örn: "belgede yok" yanıtı, kaynak gösterimi, retrieval threshold, self-check, min-ilişki skoru)_
- **Gerekçe:**
- **Alternatifler:**
- **Karar tarihi:**

### 3.8. Yapılandırma / Ortam
- **Seçim:** `.env`, `docker-compose.yml` + per-servis `Dockerfile`
- **Gerekçe:**_(doldurulacak)_
- **Alternatifler:**_(doldurulacak — örn: bare-metal `uv run` / `npm run dev`)_
- **Karar tarihi:** 14.09.2026

**Docker akışı (canlı dev — brüv modeli):**
- `docker compose up -d --build` → `db` (Postgres) + `web-api` (uv/FastAPI `--reload`) + `web` (Vite dev server + HMR) + `caddy` (opsiyonel :8080 proxy)
- `web` kaynak kodunu bind-mount eder (src/public/index.html/vite.config); imajdaki `node_modules` canlıdır → dosya kaydet, tarayıcıda anında yansır (build yok)
- `web-api` kaynağı bind-mount eder + uvicorn `--reload` → `.py` kaydet, otomatik restart; `chroma_data` ve `storage` host'ta kalır
- `caddy` port 8080 → 80; `/api/*` → `web-api:8000`, geri kalan → `web:5173` (Vite dev; nginx yerine Caddy — config ana dizindeki `Caddyfile`)
- `web-api` port 8000 (debug için opsiyonel); healthcheck: `GET /api/health`
- Alternatif — Docker'sız: `scripts/dev.sh` → backend `uv run uvicorn --reload` (:8000) + frontend Vite HMR (:5173), `/api` proxy Vite üzerinden.

---

## 4. Proje Dizin Yapısı (hedef)

```
folyo/
├── arch.md            ← bu doküman
├── DEVLOG.md          ← geliştirme günlüğü (teslimat #1)
├── TESTING.md         ← test senaryoları + sonuçlar (teslimat #2)
├── README.md          ← kurulum/çalıştırma (teslimat #5)
├── case_study.docx    ← orijinal case study
├── web/               ← frontend (React + Vite + Tailwind + daisyUI)
│   ├── src/
│   ├── public/
│   ├── Dockerfile     ← (artık kullanılmıyor; dev imajı `Dockerfile.dev`)
│   └── .dockerignore
├── web-api/           ← backend API (FastAPI + uv)
│   ├── app/           ← FastAPI uygulaması
│   │   ├── main.py
│   │   ├── services/  ← ocr, indexing, retrieval, qa
│   │   └── tests/
│   ├── Dockerfile     ← uv tabanlı
│   └── .dockerignore
├── Caddyfile          ← caddy servisi: SPA statik serve + /api proxy (nginx yerine)
├── docker-compose.yml ← caddy + web + web-api (network: folyo-net)
├── data/              ← örnek belgeler, test fixture'ları
├── scripts/           ← kurulum / demo / test scriptleri
└── docker/            ← (opsiyonel) container tanımları
```

---

## 5. Açık Kararlar / Yapılacaklar

- [x] Web katmanı kurulumu (web + web-api klasörleri) — 14.09.2026
- [x] Dockerize etme (compose + Dockerfiles) — 14.09.2026
- [ ] OCR motoru seçimi + TR/EN doğrulama (3.3)
- [ ] Embedding + vector store seçimi (3.4, 3.5)
- [ ] LLM ve hallucination guard stratejisi (3.6, 3.7)
- [ ] Proje iskeletinin kurulması
- [ ] İlk uçtan uca MVP akışı
- [ ] TESTING.md senaryo seti

---

## 6. Notlar / Log

| Tarih | Karar / Değişiklik |
|---|---|
| 14.09.2026 | arch.md oluşturuldu; case study analiz edildi |
| 14.09.2026 | Web katmanı kararı: `web/` (React+Vite+Tailwind+daisyUI), `web-api/` (FastAPI+uv); klasörler kuruldu |
| 14.09.2026 | Docker: `docker-compose.yml` — web (nginx:8080, /api proxy) + web-api (:8000, healthcheck); uçtan uca doğrulandı |
| 09.09.2026 | nginx kaldırıldı → Caddy; `Caddyfile` ana dizinde (tek Caddy: statik serve + /api proxy, web-static volume). `web` tek seferlik build servisi oldu |
| 09.09.2026 | **Canlı dev stack — brüv modeli**: `docker-compose.dev.yml` silindi; tek `docker-compose.yml` → web = Vite dev (bind-mount + HMR, Dockerfile.dev), web-api = uvicorn `--reload` (bind-mount), caddy :8080 proxy → `web:5173`; statik build / `web-static` volume kaldırıldı. Kod düzenle → anında yansır, build gerekmez |
| 09.09.2026 | **Basit RAG** (web-api): `.env` (gitignore'lu, anahtarlar boş), Nemotron 3 Ultra (streaming) + Nemotron 3 Embed 1B; fazlar `extracting→chunking→embedding→done`; numpy+`.ragdata`; POST/GET/DELETE `/api/documents` (SSE) + POST `/api/qa` (SSE). Sahte OpenAI-uyumlu modelle uçtan uca + restart kalıcılığı doğrulandı; ön yüz gerçek API'ye bağlandı (`lib/api.js`) |
| 09.09.2026 | Orijinal dosyalar depolanıyor: `.ragdata/files/<doc_id>/<ad>`; chunk'lama depodaki kopyadan; `storing` fazı (UI loading) + `GET /api/documents/{id}/file` indirme; DELETE dosyayı da siler. Doğrulandı |
| 09.09.2026 | **Workspace mimarisi + Postgres + ChromaDB**: sohbet=workspace (ad ilk mesajdan, 60 karakter); tablolar `workspaces/documents/chat_messages/embeddings` (SQLModel, enum durumlar, CASCADE); vektörler ChromaDB'de (workspace-scope'lu retrieval); dosyalar `storage/<doc_id>/`; stream'li upload (X-Filename, ortası iptal→cancelled) + XHR progress + embedding batch iptal; restart'ta stale'ler failed. Sahte modelle uçtan uca + restart kalıcılığı doğrulandı |