# Folyo — Çekirdek RAG & Ingestion Mimarisi Teknik Şartnamesi (ADR)

> **Durum:** 🔒 Kilitlendi — 14.09.2026
> Bu doküman **hedef (ulaşılacak) mimaridir**; kod bu noktaya taşınacaktır.
> Her karar **Karar / Gerekçe / Alternatif** formatında kayıtlıdır.

---

## 0. Çelişki Kaydı — Kapanış Durumu

`rag_arch` hedefi ile kodun/DEVLOG'un ayrıştığı 8 nokta karara bağlandı:

| # | Konu | Karar |
|---|---|---|
| **C1** | Füzyon yöntemi | **RRF (k=60)**. Min-max normalize + ağırlıklı toplam (`bm25_weight`) terk edildi. |
| **C2** | Halüsinasyon kalkanı | **Çift ham sinyal:** `dense cosine ≥ 0.38` (BGE-M3) **VEYA** `ham BM25 ≥ 1.0` (kalibre edildi). Rozet: dense katkılı kesişim koşulu (`dense ≥ 0.38` VEYA güçlü `BM25 ≥ 1.0`); dense sıfırsa rozet %75-80 bandında (orta/dolaylı) kalır. |
| **C3** | BM25 kapsamı | **Workspace-geneli** bağımsız indeks; lazy in-memory cache + add/delete'te invalidation. Aday-kümesi BM25'i terk edildi. |
| **C4** | Metadata | `page_number`, `content_type`, `page_context`, `bbox[]` eklendi; **sayfa-farkında** chunking. |
| **C5** | OCR | **Tesseract (tur+eng)** → yoğunluk testi → gerekirse **Vision LLM**. |
| **C6** | Kütüphane | **PyMuPDF (fitz)**. `pypdf` terk edildi; `pdfplumber` şimdilik eklenmedi. |
| **C7** | Chunk | ~1400 karakter (≈600–800 token), **sayfa sınırına saygılı**, %15 overlap, başlık takipli `page_context`. |
| **C8** | UX üretimi | Deterministik **kimlik kartı** + tek LLM çağrısıyla **özet & starter sorular** (non-blocking). |

---

## 1. Mimari Prensipler & Tasarım Felsefesi

* **Zero-Magic / Vanilla Çekirdek:** LangChain, LlamaIndex gibi soyutlama katmanları kullanılmaz. Doğrudan resmi SDK'lar (`openai`-uyumlu HTTP, `chromadb`) ve saf Python bileşenleri ile uçtan uca kontrol sağlanır.
* **Hibrit ve Asimetrik Eşleşme Güvencesi:** Semantik arama kör noktaları (spesifik kodlar, madde numaraları, dövizli tutarlar) ve kelime eşleşmesi tuzakları (farklı ifade edilen aynı kavramlar) **birbirinden bağımsız iki retriever** ile telafi edilir. *(Kritik: iki retriever de tüm workspace'i tarar; hiçbiri diğerinin adaylarına hapsedilmez.)*
* **İki Katmanlı Güvenlik Kalkanı (Deterministic Guardrail):**
  1. **Katman 1 (deterministik):** LLM'den önce çift ham sinyal eşiği. Yetersizse LLM hiç çağrılmaz.
  2. **Katman 2 (prompt):** Sistem prompt'u, bağlamda olmayan bilgiyi üretmeyi yasaklar.
* **Ürün Odaklı İndeksleme (Immediate UX):** Yükleme tamamlanınca **deterministik kimlik kartı** anında; **özet + başlangıç soruları** ise bloklamadan arka planda üretilir.

---

## 2. Ingestion (Belge Ayrıştırma, Zenginleştirme & Chunking) Hattı

### 2.A Karar Ağacı

```text
Sayfa (PyMuPDF / fitz)
│
├─ page.get_text("blocks") ──► dijital metin katmanı
│     • başlık/altbilgi: dikey alanın ilk %7 / son %7 budanır
│     • bloklar (x0, y0) koordinatına göre sütun sırasına dizilir   ← multi-column
│     • page.find_tables() → Markdown tablo → content_type = "table" (bölünmez, tek chunk)
│
├─ page.get_images() ──► boyut filtresi (< 100x100 px ele) → kalanlar bbox'ıyla tutulur
│
└─ KARAR: sayfa seçilebilir metin içeriyor mu?
      EVET ve büyük görsel yok → dijital akış yeterli
      HAYIR (metin katmanı yok) VEYA büyük görsel var →
            ┌─ Tesseract OCR (tur+eng)                        (~300 ms, $0)
            ├─ yoğunluk testi:  mean_conf ≥ 70
            │                   ∧ alnum_ratio ≥ 0.75
            │                   ∧ word_count ≥ 10
            │                   ∧ metin_kapsama ≥ %5       ← "resmin çoğu yazı mı?"
            ├─ EVET → content_type = "ocr_text"        (Tesseract kabul)
            └─ HAYIR → Vision LLM → {scanned_page | image_caption | diagram | form_data}
```

**Büyük görsel eşiği:** görsel alanı ≥ sayfa alanının **%15'i** VEYA ≥ **300x300 px** ise işleme alınır; altı elenir.

### 2.B İçerik Türleri — Üretim Yolu ve Kararlar

`content_type` = **"bu metin hangi yoldan üretildi"** etiketidir. Ayrı bir sınıflandırıcı eğitilmez; tür, üretim yolundan doğar.

| Tür | Üretim yolu | Karar | Gerekçe / Alternatif |
|---|---|---|---|
| `text` | PyMuPDF blok okuma + sütun sıralama + header/footer budama | **Çekirdek** | Alternatif: `pypdf` (blok/bbox/isimli yapı yok — terk edildi) |
| `table` | `page.find_tables()` → Markdown | **KEEP** | Fatura/ekstre için yüksek değer. Alternatif: `pdfplumber` (şimdilik gereksiz ek bağımlılık) |
| `ocr_text` | Tesseract (tur+eng), yoğunluk testini geçerse | **KEEP** | case study zorunlu (JPG/PNG + TR/EN). Maliyet: sistem bağımlılığı |
| `scanned_page` | Vision LLM — tam sayfa metne döküm / yapı | **KEEP** (eşikli) | Form, mühür, el yazısı, düşük kalite tarama. Maliyet: API |
| `image_caption` | Vision LLM — gömülü grafik/şema analizi | **KEEP** (boyut eşikli) | Grafiğin anlamı görsel olmadan kaybolur |
| `diagram` | Vision LLM — yapılandırılmış adımlar (+ ops. Mermaid) | **KEEP** | Aynı Vision çağrısının içinde, ek maliyet yok |
| `form_data` | Dijital: PyMuPDF `page.widgets()` · Taranmış: Vision şeması | **KEEP** | DEVLOG'un asıl derdi (fatura no / TC no / tutar birebir) |
| `equation` | Ayrı LaTeX modeli **yok** | **FOLD** | Genel belgede nadir (düşük fayda) / pix2tex·nougat entegrasyonu pahalı. Dijital denklem `text`, taranmış denklem `scanned_page`/Vision içinde eritilir. Tür desteklenir, özel pipeline kurulmaz |

### 2.C Katmanlı OCR & Akıllı Vision Fallback

Harici Vision API maliyetini ve gecikmesini düşürmek için önce yerel Tesseract denenir; **çıktının "çoğu yazıdan oluşup oluşmadığı"** ölçülür:

| Metrik | Eşik | Anlam |
|---|---|---|
| `mean_conf` | ≥ 70 | Tesseract ortalama güven skoru |
| `alnum_ratio` | ≥ 0.75 | Alfanümerik karakter oranı |
| `word_count` | ≥ 10 | Anlamlı kelime sayısı |
| `metin_kapsama` | ≥ %5 | OCR metin bbox alanı / görsel alanı — "resmin çoğu yazı mı?" |

Dördü de sağlanırsa → `ocr_text`. Sağlanmazsa → Tesseract çıktısı **atılır**, görsel Vision LLM'e gider.

### 2.D Chunking & Sayfa-Farkında Strateji

* **Boyut:** ~1400 karakter (≈600–800 token).
* **Overlap:** %15 (~200 karakter).
* **Sayfa sınırına saygı:** chunk'lar tek sayfa içinde üretilir → her chunk **tek bir `page_number`**'a atfedilebilir. Bu, kaynak önizlemede ilgili yeri vurgulamanın ön koşuludur.
* **Parent bağlam:** Ayrı bir parent-child veritabanı yerine, **başlık takibi** ile üretilen `page_context` metadata'sı kullanılır (PyMuPDF font-size/bold'dan heading tespiti; contract'larda "Madde 14.2" gibi). Basit fallback: sayfanın ilk ~200 karakteri.
* **Tablo:** bölünmez; tek chunk (embedding modeli 32K bağlam — sığar).

### 2.E Veri Modeli (Segment → Chunk)

```python
# extract.py çıktısı
Segment(
    content_type: str,      # text | table | image_caption | ocr_text | scanned_page | form_data | diagram
    text: str,
    page_number: int,       # 1 tabanlı
    bbox: list[tuple],      # [(x0, y0, x1, y1), ...]
    order: int,             # sayfa içi okuma sırası
)

# embed girdisi
Chunk(
    text: str,
    content_type: str,
    page_number: int,
    page_context: str,
    chunk_index: int,       # doküman geneli sıra
    bbox: list[tuple],      # chunk birden fazla bloğu kapsayabilir → liste
)
```

### 2.F Nihai ChromaDB Metadata Şeması

> Chroma metadata değerleri **skaler** olmalıdır (str/int/float/bool). `bbox` bu nedenle **JSON string** olarak saklanır.

```python
metadata = {
    "workspace_id": "ws_12345",       # tenant/çalışma alanı izolasyonu
    "document_id": "doc_67890",       # belge kaydı
    "name": "sozlesme.pdf",           # kaynak dosya adı
    "page_number": 4,                 # 1 tabanlı sayfa
    "chunk_index": 12,                # doküman geneli parça sırası
    "content_type": "table",          # text|table|image_caption|ocr_text|scanned_page|form_data|diagram
    "page_context": "Bölüm 3: Ödeme Hükümleri ve Cezai Şartlar",
    "bbox": "[[72.0, 130.5, 520.0, 410.2]]",   # JSON string — highlight için
}
```

> **Kod migrasyonu:** mevcut `doc_index` alanı → `chunk_index` olarak yeniden adlandırılır (`llm.py`'deki `doc_index + 1` referansı güncellenir).

### 2.G Vision Sağlayıcı (İkinci Sağlayıcı)

Görsel işleme için **ayrı, OpenAI-uyumlu** bir vision modeli kullanılır.

* **Ayarlar (`.env`):** `VISION_API_KEY`, `VISION_BASE_URL`, `VISION_MODEL`.
* **Fallback:** `VISION_API_KEY`/`VISION_BASE_URL` boşsa `LLM_*` değerlerine düşer; `VISION_MODEL` zorunludur.
* **Hazır istemci:** `services/vision.py` → `analyze_image()` / `describe_image(purpose)`; istek gövdesi `content: [{type:"text"}, {type:"image_url", image_url:{url:"data:<mime>;base64,...", detail}}]`.
* **Amaç → prompt eşlemesi:** `VISION_PROMPTS` (`core/constants.py`) — `scanned_page | image_caption | diagram | form_data`. Her prompt "uydurma, birebir aktar, belgenin dilini koru" kurallarını taşır.

---

## 3. Retrieval (Geri Çağırma) & Guardrail Hattı

### 3.A Akış

```text
                        [Kullanıcı Sorusu]
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼                                               ▼
[Dense Vektör Arama]                           [Sparse Terim Arama]
ChromaDB (kosinüs)                             Workspace-geneli BM25
top_k = 8                                      top_k = 8
        │                                               │
        └───────────────────────┬───────────────────────┘
                                ▼
                   [Reciprocal Rank Fusion — k = 60]
                      Tekil sıralama, ilk 8 aday
                                │
                                ▼
                 [Çift Sinyalli Güvenlik Kalkanı — ham skorlar]
             (dense_sim ≥ 0.30 VEYA ham bm25 ≥ 1.0)?
                                │
                ┌───────────────┴───────────────┐
                ▼ (HAYIR)                       ▼ (EVET)
      [LLM Çağrısını Kes]              [İlk 5 Chunk Seç]
      Standart Red Yanıtı                      │
                                               ▼
                                     [LLM Yanıt Üretimi]
                                     LLM_MODEL streaming
                                     + Güven Rozeti (ham sinyallerden)
```

### 3.B BM25 — Workspace-Geneli & Cache'li *(C3)*

* İndeks, workspace'teki **tüm** chunk'lar üzerinde kurulur — dense adaylarının üzerinde değil.
* **Lazy in-memory cache:** `_bm25_cache: dict[ws_id, (epoch, BM25Okapi)]`. İlk sorguda Chroma'dan `collection.get(where={"workspace_id": ...})` ile metinler çekilir, indeks kurulur.
* **Invalidation:** belge ekleme/silme o workspace'in cache'ini düşürür. Yeniden başlatmada ilk sorguda yeniden kurulur (kalıcı pickle yok).
* **Gerekçe:** IDF ancak tüm korpus üzerinde anlamlıdır; aksi halde sparse recall, dense recall'a hapsolur ve birebir eşleşme (fatura no / TC no) kaybolur.
* **Alternatifler:** kalıcı BM25 (gereksiz karmaşıklık) · Elasticsearch/OpenSearch (MVP için ağır).

### 3.C Custom Tokenizer

Teknik kodların, madde numaralarının ve tutarların (`TR-2024-X9`, `Madde 14.2`, `4.850 TL`) noktalama ile parçalanmaması için:

```python
import re

def tokenize_text(text: str) -> list[str]:
    cleaned = text.lower()
    compounds = re.findall(r"[a-z0-9_]+(?:[-./][a-z0-9_]+)*", cleaned)
    tokens: list[str] = []
    for token in compounds:
        tokens.append(token)                  # bileşik hali korunur
        parts = re.split(r"[-./_]+", token)   # alt parçalar da eklenir (recall)
        if len(parts) > 1:
            tokens.extend(p for p in parts if p and p != token)
    return tokens
```

### 3.D Füzyon — Reciprocal Rank Fusion *(C1)*

$$RRF(d) = \sum_{m \in \{\text{dense}, \text{bm25}\}} \frac{1}{60 + r_m(d)}$$

* **Karar:** RRF.
* **Gerekçe:** Sıra tabanlı, ölçekten bağımsız, **kalibrasyon gerektirmez** — 5 chunk'lı ve 5000 chunk'lı belgede aynı davranır. Yerel re-ranker'ın 2–4 sn CPU gecikmesini de getirmez.
* **Alternatif (değerlendirildi, reddedildi):** Convex Combination (normalize edilmiş ağırlıklı skor). Bir BM25 outlier'ını (exact-match) daha iyi taşır ama min-max normalizasyon query'ye bağlı ve dengesizdir (tek büyük skor diğerlerini ezer; tüm skorlar yakınsa gürültü şişer).
* **RRF'in bilinen zayıflığı ve telafisi:** Yalnızca tek kanalda yakalanan güçlü bir sinyali bastırabilir. Telafi: (1) her retriever'dan **geniş derinlik** (8+8), (2) guardrail **ham sinyallerden** çalışır → exact-match chunk BM25 sinyaliyle LLM yolunu garantiler.
* **Alternatif (değerlendirildi, reddedildi):** Hypothetical Document Embeddings (HyDE) — gecikme + maliyet; hibrit yapı zaten yeterli.

### 3.E Çift Sinyalli Halüsinasyon Kalkanı *(C2)*

```python
top_dense_sim  = max(h["score"] for h in dense_hits)     # ham kosinüs
top_bm25_score = max(bm25_raw_scores)                    # ham BM25

is_dense_confident = top_dense_sim  >= settings.guard_dense_min   # 0.38
is_bm25_confident  = top_bm25_score >= settings.guard_bm25_min    # 1.0

if not (is_dense_confident or is_bm25_confident):
    return {
        "status": "rejected",
        "answer": "Yüklenen belgelerde bu soruya dair doğrudan bir bilgi bulunamadı.",
        "confidence_score": round(top_dense_sim * 100, 1),
    }
```

* **Kalibrasyon (14.09.2026):** `text-embedding-3-small` + Türkçe kısa sorgularda ölçüldü — ilgili chunk kosinüs bandı ~0.24–0.42; alakasız sorgular da ~0.35–0.43'e çıkıyor (mutlak kosinüs ayrıştırmıyor). BM25 ham skoru 7 chunk'lık korpusta ~2.1 ile sınırlı. Eşikler `0.30 / 1.0`'a çekildi; böylece OR kanalı gerçekten çalışıyor. İkisi de `.env` (`GUARD_DENSE_MIN`, `GUARD_BM25_MIN`) ile değiştirilebilir; kesin kalibrasyon TESTING.md'de.

### 3.F Güven Skoru Rozeti *(C2/§3D)*

Rozet, **RRF skorundan değil ham sinyallerden** türetilir (RRF skoru ~0.02 mertebesinde, gösterime uygun değil):

| Seviye | Aralık | Koşul |
|---|---|---|
| Yüksek | %85–98 | Her iki kanaldan da üst sırada ≥ 2 doğrulanmış kaynak |
| Orta / Dolaylı | %65–84 | Tek kanaldan çıkarım (yalnız dense veya yalnız BM25) |
| Yetersiz | < %65 | Çift sinyalli kalkanın devreye girdiği durum (LLM çağrılmaz) |

### 3.G Retrieval Ayarları (`core/config.py`)

```python
retrieve_dense_k: int = 8       # dense top-k
retrieve_bm25_k:  int = 8       # sparse top-k (workspace-geneli)
rrf_k:            int = 60      # RRF sabiti
context_chunks:   int = 5       # LLM'e giden chunk sayısı
guard_dense_min:  float = 0.38  # BGE-M3 (ham kosinüs eşiği)
guard_bm25_min:   float = 1.0   # ham BM25 eşiği
```

> Kaldırılanlar: `top_k`, `bm25_weight`, `similarity_threshold`.

---

## 4. İndeksleme Anı UX — Kimlik Kartı, Özet & Başlangıç Soruları

### 4.A Belge Kimlik Kartı *(deterministik, LLM yok)*

Ingestion'ın zaten ürettiği veriden hesaplanır — **sıfır ek maliyet**:

```
7 sayfa · 42 parça · 3 tablo · 2 grafik · 1 diyagram · 1 form · 0 taranmış sayfa
```

`equation` sayısı **gösterilmez** (FOLD edildi; sürekli 0 gösteren metrik güveni düşürür).

### 4.B Özet + Başlangıç Soruları *(tek LLM çağrısı, non-blocking)*

* **Girdi:** başlık blokları + **stratified örnek** (ilk + orta + son chunk), ~2000 token bütçesi. *(Spec'teki "ilk 2-3 chunk" çok sayfalı belgede yalnız 1. sayfayı görürdü.)*
* **Çıktı:** 2–3 cümle özet + 3 tıklanabilir başlangıç sorusu — tek çağrıda, `LLM_MODEL` ile, belgenin dilinde.
* **Zamanlama:** belge `embedded` olduktan **sonra** arka planda. Kart anında görünür; özet/sorular hazır olunca gelir. Belge, embedded olduğu an sorulabilir.
* **Hata toleransı:** çağrı patlarsa belge `embedded` kalır, `summary=null`. Özet hatası belgeyi **asla** `failed` yapmaz.
* **Sorular cevaplanabilir olmalı:** prompt, yalnızca verilen içerikten cevaplanabilecek sorular üretmeyi şart koşar (demo'da belgenin cevaplayamayacağı soru önermemek için).

### 4.C Depolama

* **Özet:** `documents.summary` (TEXT) — belgeyle 1:1.
* **Başlangıç soruları:** ayrı **`document_questions`** tablosu (1:N):

```python
class DocumentQuestion(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID = Field(foreign_key="document.id", ondelete="CASCADE")
    question: str
    position: int          # görüntüleme sırası (0..2)
    created_at: datetime
```

### 4.D UI Kuralı

Başlangıç soruları, sohbetin **boş durumunda üstte** gösterilir — **yalnızca workspace'te henüz hiç kullanıcı mesajı yoksa**. Kullanıcı ilk soruyu sorduğu anda öneriler kaybolur.

---

## 5. Uygulama Sırası

1. **PyMuPDF + `Segment` modeli:** metin/tablo çıkarımı, sütun sıralama, header/footer, `page_number` + `bbox`.
2. **OCR kademesi + Vision fallback:** Tesseract (tur+eng), yoğunluk testi, `VISION_PROMPTS` ile `{scanned_page, image_caption, diagram, form_data}`.
3. **`Chunk` modeli + metadata migrasyonu:** `content_type`, `page_number`, `page_context`, `bbox`, `chunk_index` (Chroma yeniden indeksleme).
4. **Retrieval refactor:** workspace-geneli BM25 cache, RRF, çift sinyalli guardrail, yeni config.
5. **§4 üretimi:** `documents.summary` + `document_questions` + async job + UI boş-durum kuralı.
6. **Kalibrasyon & doküman senkronu:** `TESTING.md` ile eşik kalibrasyonu; `arch.md`'nin güncellenmesi (⚠️ `arch.md` §3.5 vektör deposu hâlâ "numpy" diyor — kod ChromaDB kullanıyor).

---

## 6. Karar Günlüğü

| Tarih | Karar |
|---|---|
| 14.09.2026 | C1–C8 kilitlendi. Ingestion: PyMuPDF + Tesseract→Vision; `equation` FOLD. Retrieval: workspace BM25 + RRF(k=60) + çift ham sinyal. UX: deterministik kart + non-blocking özet/sorular. Vision ikinci sağlayıcı altyapısı kuruldu (`services/vision.py`, `VISION_PROMPTS`). |
| 14.09.2026 | **Guardrail kalibrasyonu:** canlı ölçüm (text-embedding-3-small, TR kısa sorgu, 7-chunk korpus): ilgili chunk kosinüsü 0.24–0.42 bandında, BM25 ham ~2.1. `0.72/4.0` bu kombinasyonda ulaşılamazdı → `0.30/1.0`'a çekildi. Sparse kanal yeniden aktif; eşikler `.env`'den değiştirilebilir. |
| 14.09.2026 | **Workspace düzeyi:** `documents.summary_status` (pending/done/failed) + `workspaces.summary` + `workspaces.summary_docs` (doc-set imzası). Soru sayısı 1–6 (LLM karar verir, eşik yok). Workspace özeti+başlık: imza + gate (pending varsa bekle; hiç done yoksa üretme; failed hariç). Başlık: LLM → `workspaces.name`; ilk-soru fallback'i kaldırıldı. |
| 14.09.2026 | **Embedding → `BAAI/bge-m3`** (dim 1024; eskisi text-embedding-3-small 1536). Temiz sayfa. Ölçüm: alakalı 0.686 / aynı-belge 0.274 / alakasız 0.248 — eski modelde ayrışma yoktu (0.33/0.43), artık net. `guard_dense_min` 0.30 → **0.45**. BM25 kanalı (kendi rank_bm25) değişmedi. |
| 15.09.2026 | **Güvenlik/robustness paketi (A2–A7):** (1) header/footer artık sabit orana ek olarak frekans temelli — üst/son %10 bandında sayfaların ≥%60'ında tekrar eden (metin, y-bandı) seti suppress listesi yapılır, çift satırlı header sızması da budanır; (2) diyagram bekçisi: OCR 4 metrik geçse bile `word_count < 25 ∧ coverage < %15` → tip `image` (OCR metni içerik, Vision'sız); `ocr_min_alnum_ratio` 0.70 → 0.75 (ADR §2C ile senkron); (3) tablo `> 4000 karakter` → satır bazlı bölme (caption+başlık her parçada tekrarlanır) — embed truncate koruması; (4) XY-cut yalnızca metin/kod bloklarına uygulanır, tablo/görsel y-konumuna göre sonradan enjekte edilir; (5) Chroma'daki "dimension" hatası artık koleksiyonu **asla resetlemez** — `embed_dim/embed_model` koleksiyon metadata'sında tutulur, uyuşmazlık açıklayıcı hata verir (manuel reset opsiyonel). |
| 15.09.2026 | **BM25 Stage-1 (ölçek dayanıklılığı, §3B/C3):** `invalidate()` artık cache'i düşürüp bir sonraki sorguda event loop'u bloklayarak rebuild yerine — **dirty + revizyon sayacı** kurar; `get_index` bayat indeksi (stale-serve) döndürür ve rebuild'i **arka planda** tetikler (`asyncio.Task` + per-ws tek-build garantisi, done-callback kimlik kontrolü). BM25Okapi kurulumu `anyio.to_thread`'a taşındı (CPU ağır iş event loop'ta kalmaz); API hiçbir noktada rebuild'de bloklanmaz. Build sırasında yeni invalidate gelirse revizyon kontrolü bayrağı yeniden kurar (konverjans) — cache asla yanlış "temiz" kalmaz. Soğuk başlangıç build'i await eder (loop serbest), hata yeniden fırlatılır (yanıltıcı "belge yok" yok). `clear_workspace()` ile workspace silinirken durum alanları boşaltılır. |
| 15.09.2026 | **Blok denklem hattı (equation, C-karar geri alındı):** Inline denklemler Unicode/text akışında kalır. Blok denklem `is_block_equation` ile tespit: matematik fontu (cmsy/cmmi/CM/Cambria Math/STIX…) VEYA sembol oranı ≥ 0.25 (kısa denklem kuralı: ≤12 karakter + ≥1 sembol) + geometri (ortalanma ≥ %15/%85 VEYA sondaki denklem numarası). **Aşama 1 (yerel, $0):** `pylatexenc` → Unicode→LaTeX (`\ensuremath` sadeleştirmesi + sondaki (N) numarası soyulur; çıktı yapısal olarak değerli değilse reddedilir). **Aşama 2 (Vision fallback):** yerel çözemezse VEYA Office PUA glifleri (U+E000–U+F8FF) varsa → bbox kırpılır (`equation_vision_dpi=200`, padding 6) → `VISION_PROMPTS["equation"]` ile saf `$$…$$` LaTeX. Vision yoksa raw Unicode korunur. Chunk: `text`+`equation` segmentleri aynı grupta birleşir (sayfa başına mini-chunk şişmesi ve bağlam kopukluğu önlenir); saf denklem grubu `content_type=equation`. Yeni bağımlılık: `pylatexenc>=2.11`. |
| 15.09.2026 | **Kesikli rozet → sürekli güven skoru (B3):** `92/82/80/75/72` merdiveni terk edildi; `confidence_score()` formülü (ağırlıklar toplamı = 100): `dense bileşeni 58·norm01(top_dense, 0.15, 0.70)` + `bm25 bileşeni 24·norm01(log1p(top_bm25), 0, log1p(5))` + `uzlaşma 18·(kalifiye kesişim / context_k)`. Kural: dense tamamen yokken güçlü BM25 (`b≥0.5`) → 74-78 bandı (eski "dense sıfırsa %75-80" kararının sürekli karşılığı); kalkan geçmiş sorgu daima ≥55 (yetersiz rozeti yalnız reddedilen analamında). Seviyeler: ≥85 yüksek / ≥65 orta / ≥45 dolaylı / <%45 yetersiz. Tüm sabitler `.env`'den (`CONFIDENCE_*`) kalibre edilir — kullanıcı loglarında false-rejection oranına göre norm aralıkları (dense 0.15/0.70 → mevcut bge-m3 ölçümleri 0.25-0.69) ve ağırlıklar ayarlanır. |
| 15.09.2026 | **Güven formülü → taşıyıcı (carrier) modeli (B3 canlı doğrulama):** Canlı sorgu ("unsuz muzlu pankek'in içinde neler var", e60329cf): dense 0.247 (eşik altı) + BM25 6.82 (nakavt) + 5/5 uzlaşma → eski formül dense-baskın olduğu için ham 52'de kalmış, tablo 55 tabanına çakılmıştı (yanıltıcı "dolaylı"). Tek-formül `58·d+24·b+18·c` terk edildi; **iki bağımsız yol** (her yolun ağırlıkları toplamı 100): dense yolu `92·d + 8·c`, bm25 yolu `64·b + 28·c + 8·d`; kanıtı taşıyan yol skoru belirler (`max`). Kurallar korunur: dense-kör + güçlü BM25 taban 74; cevap üretilen sorgu taban 55. Aynı sorgu artık **93 · yüksek**. Yapısal listeli/nesne-çokluğu yüksek chunk'larda BGE-M3 dense benzerliği doğal olarak düşük (0.25 bandı) — BM25 kanalı bu senaryonun taşıyıcısıdır. |
| 15.09.2026 | **BM25 Türkçe tokenizer + kök eşleşmesi (§3B/C3):** Canlı sorguda ("kahveli pankeki ne zaman çevirmeliyim") kanıt: eski tokenizer `[a-z0-9_]+` ASCII-only idi — `ç ş ğ ö ü ı` token'lardan düşüyor, "çıktığında" → `kt`,`nda` diye parçalanıyordu; cevap chunk'ının ("kabarcıklar çıktığında çevirmelisiniz") kendi token'ları eşleşemiyor, BM25 yalnızca başlık kelimesi "kahveli" ile 0.83'te kalıyordu. **Düzeltme:** (1) Unicode regex `[\w]+` — diakritikler korunur; (2) hafif kök eşleşmesi: sorgu token'inin ilk `bm25_stem_min=4` karakteriyle aynı ön-ekli indeks terimleri de faturalandırılır (`bm25_stem_cap=24` maliyet sınırı), tam eşleşme baskın kalır. Sonuç: cevap chunk'ı BM25 0.83→5.96 (1. sıra), qualifying 3/5→5/5, aynı sorgu 66 orta→**94 yüksek**; "unsuz muzlu pankek" regresyonu 93 yüksek (değişmedi). |
| 15.09.2026 | **Şema yönetimi:** (1) `create_all`+ALTER yerine **Alembic** (`web-api/app/alembic`, async engine, `0001_initial_baseline`, canlı `stamp`); `init_db` = stamp-if-exists/upgrade. (2) **Şema sahipliği yalnız web-api**: panel-api şema tanımı tutmaz — `autoload` read-only (psycopg sync engine), `models.py`/`sqlmodel` kaldırıldı. Yeni görüş: sütun eklemeleri `alembic revision --autogenerate` ile, yalnız web-api'de. |
