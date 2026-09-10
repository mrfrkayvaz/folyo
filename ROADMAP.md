# Folyo — RAG Yol Haritası (mevcut kod → `rag_arch.md`)

> **Hedef:** `rag_arch.md` (kilitli mimari, 14.09.2026).
> **Mevcut durum:** Çalışan "basit RAG" (pypdf + tek blob chunk + dense ağırlıklı hibrit + tek eşik).
> **İlke:** Her adım sonunda sistem çalışır kalır — artımlı ve doğrulanabilir.

---

## 0. Mevcut Durum ↔ Hedef Farkı

| Alan | Mevcut kod | `rag_arch.md` hedefi | Adım |
|---|---|---|---|
| Belge çıkarımı | `pypdf`, sayfalar birleştirilir, bbox yok | PyMuPDF: blok + bbox + sütun sıralama | 1 |
| Chunk | 900 karakter, tek blob, sayfa yok | ~1400 karakter, sayfa-farkında, `page_context` | 1–2 |
| Metadata | `doc_index`, `name` | `content_type`, `page_number`, `chunk_index`, `page_context`, `bbox` | 1–4 |
| İçerik türleri | yok | `text/table/ocr_text/scanned_page/image_caption/form_data/diagram` | 2, 4 |
| Tablo | yok | `find_tables()` → Markdown | 2 |
| OCR / görsel | `extract.py` görselde hata fırlatır | Tesseract (tur+eng) → yoğunluk testi → Vision | 4 |
| Retrieval | Aday-kümesi BM25 + min-max ağırlıklı + tek eşik `0.3` | Workspace-geneli BM25 + RRF(k=60) + çift ham sinyal | 3 |
| Kimlik kartı | yok | deterministik özet kartı | 2 (veri) / 5 (UI) |
| Belge özeti & sorular | yok | tek LLM çağrısı, non-blocking, `document_questions` | 5 |
| Güven rozeti | yok | ham sinyallerden % seviyesi | 3 (veri) / 6 (UI) |
| Kaynak vurgu | `chunkIndex` iletilir ama modal yok sayar | `page_number` + `bbox` ile sayfa atlama + vurgu | 6 |
| Görsel dosya kabulü | reddedilir | `.jpg/.png` uçtan uca | 4 |

**Hazır olanlar (Adım 0'ın bir kısmı):** `services/vision.py`, `VISION_PROMPTS`, `VISION_*` config + `vision_ready`.

---

## ✅ Adım 0 — İskele *(boyut: S, davranış değişmez)*

> **Durum: TAMAMLANDI** — `types.py` (Segment/Chunk), retrieval config, deps (pymupdf/pytesseract/pillow), Tesseract Docker imajında.

**Amaç:** Yeni veri modelini ve ayarları hazırla; hiçbir davranış değişmesin.

- `core/config.py`: retrieval ayarları eklenir — `retrieve_dense_k`, `retrieve_bm25_k`, `rrf_k`, `context_chunks`, `guard_dense_min`, `guard_bm25_min`. *(Eski `top_k/bm25_weight/similarity_threshold` Adım 3'e kadar kalır.)*
- Yeni **`services/types.py`**: `Segment(content_type, text, page_number, bbox, order)` ve `Chunk(text, content_type, page_number, page_context, chunk_index, bbox)` dataclass'ları.
- `pyproject.toml`: `pymupdf` eklenir (Adım 4 için `pytesseract`, `Pillow` de eklenir).
- **Kabul:** Uygulama aynı çalışır, import'lar temiz.

---

## ✅ Adım 1 — PyMuPDF + sayfa-farkında çıkarım & chunk *(C4, C7 · boyut: M)*

> **Durum: TAMAMLANDI** — sayfa+bbox+`chunk_index`+`content_type`+`page_context` uçtan uca; XYZ-cut sütun sıralaması; atıf `[BelgeAdı, sayfa N, parça M]` + `#page=N`; temiz sayfa (chroma/pg/storage sıfırlandı).

**Amaç:** Sayfa + bbox bilgisini uçtan uca taşı. Highlight'ın ve tür bazlı işlemenin ön koşulu.

- **`services/extract.py`** yeniden yazılır:
  - `extract_segments(filename, path) -> list[Segment]`
  - PDF: `page.get_text("blocks")` → header/footer (%7) budama → bloklar `(x0, y0)`'a göre sütun sıralaması → her blok bir `Segment(page_number, bbox, order)`.
  - TXT/MD: tek `Segment(page_number=1)`.
  - Eski `extract_text` kaldırılır (jobs yeni fonksiyona geçer).
- **`services/ingest.py`**: `chunk_segments(segments) -> list[Chunk]`; sayfa sınırına saygılı, ~1400 karakter, %15 overlap, bbox birleştirme, doküman geneli `chunk_index`.
- **`services/chroma_store.py`**: `add(...)` artık `Chunk` listesi alır; metadata: `page_number`, `chunk_index`, `content_type`, `page_context`, `bbox` (JSON string). `doc_index` → `chunk_index`.
- **`services/jobs.py`**: `extract_segments` → `chunk_segments` → embed → Chroma.
- **`services/llm.py`**: `doc_index + 1` referansı `chunk_index`'e güncellenir.
- **⚠️ Migrasyon:** Metadata şeması değiştiği için **Chroma koleksiyonu yeniden indekslenir** (dev: koleksiyonu sıfırla + belgeleri yeniden yükle).
- **Kabul:** 5+ sayfalı, 2 sütunlu PDF → her chunk doğru `page_number`; soru-cevap çalışmaya devam eder.

---

## ✅ Adım 2 — İçerik türleri (text/table) + `page_context` *(boyut: M)*

> **Durum: TAMAMLANDI** — `find_tables()` → `content_type="table"` (Markdown, bbox, kesişim filtresi); font boyutu moduyla başlık takibi (parent/child/sibling) → `page_context`; chunk grupları başlık değişince bölünür.

**Amaç:** Determinstik kimlik kartının verisini ve tablo desteğini üret.

- **`extract.py`**:
  - `page.find_tables()` → Markdown tablo `Segment(content_type="table")` (bölünmez).
  - **Başlık takibi:** PyMuPDF font-size/bold ile heading tespiti → `page_context` (fallback: sayfanın ilk ~200 karakteri).
  - Metin blokları `content_type="text"`.
- **`Chunk`**: `content_type`, `page_context` doldurulur.
- **Kimlik kartı verisi:** belge başına `content_type` dağılımı + sayfa sayısı + chunk sayısı hesaplanır (Adım 5'te `documents`'a yazılır).
- **Kabul:** Sözleşme/fatura PDF → tablo chunk'ı `content_type="table"`; `page_context` başlık taşır.

---

## ✅ Adım 3 — Retrieval refactor *(C1, C2, C3 · boyut: M)*

> **Durum: TAMAMLANDI** — workspace-geneli cache'li BM25 (`bm25_index.py`, add/delete'te invalidation) + RRF(k=60) + çift ham sinyal guardrail (0.72 / 4.0) + güven rozeti; eski `top_k/bm25_weight/similarity_threshold` kaldırıldı.

**Amaç:** Hibrit aramayı gerçekten bağımsız iki kanala ayır; füzyon ve kalkanı spec'e getir.
*(Bu adım Vision modelinden bağımsızdır — model beklenirken yapılacak en yüksek getirili iş.)*

- **Workspace-geneli BM25 cache**: `_bm25_cache[ws_id] = (epoch, BM25Okapi)`; ilk sorguda Chroma `get(where={"workspace_id": ...})` ile kurulur.
- **Invalidation**: `chroma_store.add / delete_document / delete_workspace` sonrası ilgili workspace cache'i düşer.
- **Yeni `services/retrieval.py`** (veya `rag.py` refactor):
  - Dense top-`8` + BM25 top-`8` → **RRF (k=60)** → ilk 8.
  - **Guardrail:** `max(dense cosine) ≥ 0.72` VEYA `max(ham BM25) ≥ 4.0`; değilse LLM çağrılmaz, standart red.
  - LLM'e ilk `5` chunk.
  - **Güven rozeti** ham sinyallerden hesaplanır → SSE `meta`/`done` içinde `confidence`.
- **`core/config.py`**: eski `top_k`, `bm25_weight`, `similarity_threshold` kaldırılır.
- **Kabul:** (a) "TR-2024-X9 ... tutarı?" → ilgili chunk BM25 ile gelir; (b) alakasız soru → LLM çağrılmaz; (c) rozet değeri döner.

---

## ✅ Adım 4 — OCR + Vision fallback *(C5 · boyut: L)*

> **Durum: TAMAMLANDI** — `ocr.py` (Tesseract tur+eng + 4 metrikli yoğunluk testi); async extract: tam sayfa → pixmap → OCR/`scanned_page`; metinli sayfada büyük gömülü görseller → OCR → Vision sınıflandırmalı (`classify_image` → chart/diagram/form/scan/photo); vision yokken tam sayfa/bağımsız görsel → açık hata, gömülü figür → sessiz atlama. Frontend görsel kabulü + `<img>` önizleme.
**Bağımlılık: `VISION_MODEL` (kullanıcı verecek). OCR kısmı model olmadan test edilebilir.**

- **`services/ocr.py`** (yeni): `ocr_image(bytes) -> (text, stats)` (Tesseract tur+eng) + `is_mostly_text(stats)` yoğunluk testi (`mean_conf ≥ 70 ∧ alnum ≥ 0.75 ∧ words ≥ 10 ∧ metin_kapsama ≥ %5`).
- **`extract.py`**:
  - Sayfada dijital metin yoksa VEYA büyük görsel varsa → `page.get_pixmap()` → OCR → kabul ise `ocr_text`; değilse `vision.describe_image(purpose)`.
  - `purpose` seçimi: form/fatura → `form_data`; grafik → `image_caption`; akış → `diagram`; tam sayfa metin → `scanned_page`.
  - Gömülü görseller: `get_images()` + boyut filtresi (<100px ele; ≥ sayfanın %15'i VEYA ≥300x300 işle).
- **Dockerfile**: `tesseract-ocr` + `tesseract-ocr-tur` + `tesseract-ocr-eng` sistem paketleri.
- **Frontend**: `ALLOWED_EXTS` (App.jsx) + `Welcome.jsx` metni (".jpg/.png kabul") güncellenir; `accept` attribute.
- **Kabul:** JPG fatura → `form_data`; taranmış sayfa → `ocr_text`/`scanned_page`; grafik → `image_caption`; akış → `diagram`.

---

## ✅ Adım 5 — Belge özeti + başlangıç soruları *(§4 · boyut: M-L)*

> **Durum: KOD+HİNDİRME TAMAM** — `documents.summary` + `stats` (JSONB) + `document_questions` tablosu (idempotent migrasyon); `summary.py` (başlıklar + stratified örnek → tek LLM çağrısı → JSON); jobs'ta non-blocking `_enrich_summary` (hata belgeyi asla `failed` yapmaz); API `summary/stats/starter_questions`; Frontend: kimlik kartı + özet + 3 tıklanabilir soru (yalnız boş sohbette). **Canlı LLM doğrulaması onay bekliyor (kredi kuralı).**

- **DB**: `documents.summary` (TEXT); yeni tablo **`document_questions`** (`id`, `document_id` FK CASCADE, `question`, `position`, `created_at`) + `documents`'a kimlik kartı sayımları (JSONB `stats`).
- **⚠️ Migrasyon**: `init_db`'ye idempotent `ALTER TABLE documents ADD COLUMN IF NOT EXISTS ...` ve `CREATE TABLE IF NOT EXISTS document_questions` (çünkü `create_all` mevcut tabloya kolon eklemez).
- **`services/summary.py`** (yeni): başlıklar + stratified örnek (ilk/orta/son, ~2000 token) → **`LLM_MODEL`** ile tek çağrı → 2-3 cümle özet + 3 soru (JSON).
- **`jobs.py`**: belge `embedded` olduktan **sonra** non-blocking enrich; hata → `summary=null`, belge `embedded` kalır.
- **API**: `GET /api/workspaces/{id}` ve `GET /api/documents/{id}` → `summary`, `starter_questions`, `stats`.
- **Frontend**: boş sohbette üstte kimlik kartı + starter sorular; **yalnızca `messages.length === 0`** iken; soruya tıkla → QA tetiklenir. `ReadyState` genişletilir.
- **Kabul:** Kart anında, özet/sorular birkaç sn sonra gelir; sorulmuş sohbette öneriler gizli.

---

## ✅ Adım 6 — Kaynak vurgulama & atıf derin bağlantısı *(C4'ün UX çıktısı · boyut: M/L)*

> **Durum: TAMAMLANDI (kapsam kararıyla)** — Güven rozeti + `rejected` kartı UI'da; atıf `[BelgeAdı, sayfa N, parça M]` + `#page=N` (Adım 1'de). Kalan: `#page=N`'in tarayıcıda canlı doğrulaması (blob URL fragmanı kullanıcıda) ve pdf.js bbox vurgusu — **kullanıcı kararıyla ertelendi** ("sonradan düşüneceğim").

- **Atıf verisi**: LLM bağlamı `[name, sayfa N, parça M]` biçimine geçer; inline atıf + `sources` artık `page_number` ve `bbox` taşır.
- **`RichText.jsx`**: citation regex'i sayfa + parça için güncellenir.
- **`FilePreviewModal.jsx`**:
  - **Minimum**: PDF `#page=N` ile doğru sayfaya atla (tarayıcı desteği var).
  - **Tam çözüm** *(karar gerekli)*: `react-pdf` (pdf.js) ile sayfayı canvas'a çizip bbox dikdörtgenlerini overlay et → gerçek highlight. Native `<iframe>`'de overlay mümkün değil.
- **Kabul:** Atıfa tıkla → doğru sayfa açılır; (tam çözümde) ilgili blok vurgulanır.

---

## Adım 7 — Kalibrasyon & doküman senkronu *(boyut: S-M)*

- **`TESTING.md`**: TR/EN, taranmış, tablolu senaryolar; guardrail eşiklerinin (0.72 / 4.0) gerçek belgelerle kalibrasyonu; başarısızlık durumları.
- **`arch.md`**: §3.3 OCR = Tesseract→Vision; **§3.5 vektör deposu düzeltmesi (numpy → ChromaDB, stale)**; §3.7 guardrail; §5 checklist.
- **`DEVLOG.md`**: adım adım karar ve deneyim kaydı.
- **Demo/README**: yeni dosya türleri ve akış.

---

## Bağımlılık Grafiği

```text
Adım 0 (iskele)
   │
   ▼
Adım 1 (PyMuPDF + Segment/Chunk) ──► Adım 2 (tablo + page_context)
   │                                        │
   │                                        ▼
   └──────────────► Adım 3 (retrieval) ──► Adım 4 (OCR+Vision) ──► Adım 5 (özet/sorular) ──► Adım 6 (highlight) ──► Adım 7 (kalibrasyon)
```

**Önerilen sıra:** ✅ `0..6` → `7`
**Gerekçe:** Adım 1-2 veri modelini oturtur; Adım 3 (retrieval) Vision modelinden bağımsızdır → model beklenirken en yüksek getiri; Adım 4 model gelince; 5-6 UX; 7 kapanış. Vision modeli erken gelirse Adım 4, Adım 2 ile paralel yürütülebilir.

---

## Riskler / Karar Gerektiren Noktalar

| # | Risk / Karar | Öneri |
|---|---|---|
| 1 | **Chroma re-index** (metadata şeması değişti) | Dev'de koleksiyonu sıfırla + yeniden yükle; gerekirse reindex script'i |
| 2 | **DB migrasyonu** — `create_all` yeni kolon eklemez | `init_db`'ye idempotent `ALTER TABLE ... IF NOT EXISTS` |
| 3 | **PDF highlight** — native iframe overlay edemez | Önce `#page=N` jump; highlight için `react-pdf` kararı |
| 4 | **Tesseract sistem bağımlılığı** (apt + tur/eng data) | Dockerfile'a ekle; imaj boyutu artar |
| 5 | **Multi-column sıralama** her PDF'te kusursuz değil | Edge-case testleri (Adım 7) |
| 6 | **BM25 cache belleği** çok büyük workspace'te | MVP'de sorun değil; gerekirse LRU/limit |
| 7 | **Vision maliyeti/gecikmesi** | Boyut eşiği + OCR ön filtresi (Adım 4) |

---

## Case-Study Teslimat Eşlemesi

| Teslimat | Nerede karşılanır |
|---|---|
| DEVLOG.md | Her adımda günlük — Adım 7'de toparlanır |
| TESTING.md | Adım 7 (senaryolar + kalibrasyon) |
| Kaynak kod | Adım 0-6 |
| README.md | Adım 7 |
| Demo video | Adım 7 sonrası (uçtan uca akış) |
