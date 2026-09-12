### 07.09.2026

### 08.09.2026

### 09.09.2026

pdflerin birbirine karışmaması için workspace mantığı kurguladım.

yüklenen belgeler ilgili workspacelere workspace_id üzerinden bağlanıyor.

belge yüklendiğinde önce documents tablosuna belge kaydını yapıyor ve yüklendiği anda embedding işlemine gönderiliyor. süreç ön yüzden böylelikle takip edilebiliyor. belgeler yüklenene kadar soru sormaya izin verilmiyor. belgeler yüklendiğinde de input artık aktif hale geliyor.

pdf önizlemesinde ilgili yeri vurgulamayı denedim ama tam olarak ilgili yeri vurgulamayı başaramadım. farklı bir strateji deneyeceğim.

prompt sayesinde halusinasyon görmüyor.
örneğin;
türkiye'nin başkenti neresidir? diye sorduğumda bu belgede ilgili ifadenin olmadığını belirtti.

hem api tarafının hem de fronend tarafının kodlarını ai yardımıyla düzenledim. constants, types, enums gibi yapıları ortak kullanım sağlayabilmek için kendi dosyaları içerisine çektim.

uzun dosyaların oluşmaması ve tekrarlı kullanımı sağlayabilmek için iki tarafta da component yapısı uyguladım. tekrar kullanabileceğim her yeri component haline getirdim.

rag sisteminden top_k=6 şeklinde ifade dönüyordu. burada belgeyle ilgili olmayan bir şey sorduğumda belgeyle ilgisinin olmadığını tespit edebilmesine rağmen en alakalı 6 chunkı döndürdüğü için ön yüzde yararlanılan parça sayısına 6 yazıyordu. bu nedenle threshold ekledim. yani gelen chunklar bu thresholdun altında kalıyorsa değerlendirmeye dahil edilmiyor artık. bu hem llm'e gönderilen veri miktarını azalttığı için maliyet optimizasyonu ve hız sağlıyor hem de ön yüzde yararlanılan parça sayısını yanlış göstermemiş oluyor.

### 10.09.2026

basit bir rag sistemi çok spesifik bilgilerin olduğu dökümanları getirmekte zorlanıyor. çünkü burda semantik yakınlığa dikkat ediyoruz. oysa bir fatura numarası, tc no, telefon gibi bilgilerde anlam yakınlığı değil birebir eşleşme önemlidir. zaten bu numaraların da bir anlamı yoktur. burada iki seçenek çıkıyor. regex veya bm25 yöntemini kullanmak. eğer spesifik bir rag sistemi yapıyorsak yani ne tür belgelerin gelebileceğini biliyorsak burda regex ile zenginleştirilmiş bm25 kullanılabilir. mesela pdf'teki telefon kalıpları yakalatılabilir. ancak bizim sistemimizde her türlü belge yüklenebilir. bu nedenle sadece bm25 kullanacağız. tokenizer olarak da custom bir tokenizer yazacağız. numerik değerler arasındaki - işaretlerini de kapsayabilmek için.

rag sistemlerinde kullanılan yöntemlerden biri de Hypothetical Document Embeddings. bu yöntemde kullanıcıdan gelen soru direkt llm'e gönderilir. ve kullanıcı bu soruyla ne öğrenmek istiyor şeklinde gelen soru daha da detaylandırılır. bu sayede retrieve ederken semantik olarak eşleşme ihtimali yükselir. bu yöntemin dezavantajı tabi ki de gecikme ve maliyet. bm25 ve dense vektör yöntemlerimizle zaten sağlam bir mimari kurduk. yine spesifik olarak anlamsal olarak soyut soruların sorulabileceği sistemlerde kullanılabilecek bir yöntem. bizim sistemimiz için gerek yok.

kullanılan bir diğer yöntem Re-ranker metodu. retrieve edilen chunk sayısından daha çok chunk çekilerek bir re-ranker modeline gönderilir. bu modeller normalden farklı şekilde çalışıyor. yaptığı işlem gönderdiğimiz chunk ile soru arasında benzerlik ölçmek. tamamen bunun üstüne kurulular. ancak yine maliyet ve hız dezavantajı var.
bu yöntem yerine bm25 similarity score ile dense vector similarity score arasında kusursuz bir denge tutturarak burdan karma bir benzerlik skoru elde etmek ve chunkları buna göre sıralamak daha hızlı ve avantajlı bir yöntem.



basit düzeyde çalışan bir rag sistemi ortaya çıkmış oldu. şimdi llm ile konuşup tüm mimari kararları nihai hale getireceğim. bunun için de genelde kullandığım yöntem bir [arch.md](http://arch.md) dosyası içinde belli bir konudaki mimariyi adım adım llm ile konuşup son haline getirmek. bu süreçte bana sorular sormasını istiyorum. belirsiz kalan yerler varsa bana sorabilirsin diyorum. karşılıklı fikir alışverişinde bulunarak kafamdaki tüm senaryoyu onun da anlamasını sağlıyorum. hatta kafamdaki senaryoya iyileştirmelerde bulunuyor. günün sonunda bu [arch.md](http://arch.md) dosyası oluştuğunda geriye sadece iyi bir modelin bu dosyayı koda dökmesi kalıyor.

### 11.09.2026

### 12.09.2026

### 13.09.2026

### 14.09.2026

rag_arch.md'yi kesin mimari hâline getirdim: tüm kararlar "Karar/Gerekçe/Alternatif" formatında kilitlendi (ADR). C1–C8 çelişkileri tek tek karara bağlandı.

ROADMAP.md çıkardım — mevcut kod → rag_arch hedefi için sıralı yol haritası (8 adım). Sıra onayı: retrieval (3) OCR/Vision'dan (4) önce, çünkü vision modeli bekleniyor.

**Adım 0 + Adım 1 tamamlandı:**
- `pypdf` → **PyMuPDF** geçişi. `extract.py` artık `Segment` (sayfa + bbox + içerik türü) üretiyor; XY-cut ile 2 sütunlu sayfalarda sol→sağ sıra doğrulandı; üst/alt bilgi %7 budaması çalışıyor.
- Chunk'lama sayfa-farkında: ~1400 karakter, %15 overlap, bbox listesi, doküman geneli `chunk_index`. `segment → chunk` veri modeli (types.py).
- Chroma metadata: `page_number`, `content_type`, `page_context`, `bbox` (JSON), `chunk_index`. `doc_index` kaldırıldı.
- Atıf formatı `[BelgeAdı, sayfa N, parça M]` oldu; frontend regex + CitationBadge + FilePreviewModal `#page=N` desteği güncellendi (rozetler tıklanabilir kaldı).
- Temiz sayfa: chroma_data + Postgres volume (`folyo_pgdata`) + storage sıfırlandı.
- Docker imajına Tesseract (tur+eng) eklendi; deps: pymupdf / pytesseract / pillow (pypdf çıkarıldı).

Doğrulamalar: sentetik 2 sayfalı PDF'te `extract_segments` (tür/sayfa/bbox, sütun sırası), `chunk_segments` (chunk_index/page_context), Chroma metadata round-trip, `app.main` import, Vite derlemesi — hepsi geçti. Tesseract langs: eng/tur/osd, pymupdf 1.28.2.

**Adım 2 tamamlandı (aynı gün):**
- `page.find_tables()` → `content_type="table"` (Markdown, bbox). Tablo bbox'ıyla kesişen metin blokları çift sayılmamak için atlanıyor.
- Başlık takibi: gövde font boyutu **mod** ile belirleniyor (medyan başlık tarafından şiştiği için mod doğru çıktı); parent/child/sibling mantığı → `page_context` "BOLUM 3 | Madde 14.2" gibi hiyerarşik.
- `chunk_segments` başlık bağlamı değişince grubu bölüyor → her chunk kendi başlığını taşıyor.
- Doğrulama: sentetik sözleşme PDF'si (16pt bölüm + 13pt maddeler + çizgili tablo) — tablo tek chunk, iki veri satırı korundu, başlık hiyerarşisi doğru.

**Adım 3 tamamlandı (aynı gün):**
- Workspace-geneli BM25 cache (`services/bm25_index.py`): lazy kurulum, belge ekleme/silmede invalidation (`chroma_store` üzerinden). Aday-kümesi BM25'i kaldırıldı — sparse artık dense'e hapsolmuyor (fatura no birebir eşleşme kanalı geri geldi).
- RRF (k=60) füzyon: dense 8 + bm25 8 → RRF → LLM'e `context_chunks` (5) blok.
- Çift ham sinyalli kalkan: `dense ≥ 0.72` VEYA `ham BM25 ≥ 4.0`; yetersizse LLM çağrılmıyor, standart red + `rejected` meta.
- Güven rozeti: kanal çakışmasından (yüksek 92 / orta 82 / dolaylı 72) — SSE `meta`/`done` içinde `confidence`/`confidence_level`/`rejected`.
- `core/config.py`'den eski `top_k` / `bm25_weight` / `similarity_threshold` kaldırıldı.
- Doğrulama: gerçek LLM/embedding **çağrılmadan** (sahte stub'larla): cache/invalidate ✓ · konu dışı → red + LLM çağrısı 0 ✓ · alakalı → RRF üstü doğru chunk (docA/chunk0), 5 blok, rozet 92/yüksek ✓ · compile + app.main + container reload ✓.

**Adım 4 tamamlandı (aynı gün):**
- `services/ocr.py`: Tesseract (tur+eng) + 4 metrikli yoğunluk testi. `alnum_ratio` eşiği 0.70'e çekildi — IBAN gibi noktalamalı kalıplarda 0.75 çok kırılgandı (0.74'e takıldı, TESTING.md kalibrasyon notu).
- `extract.py` async hale geldi: metin katmanı YOKSA tam sayfa pixmap → OCR → `ocr_text` veya Vision `scanned_page`; metinli sayfada büyük gömülü görseller (kenar ≥ 300px VEYA alan ≥ %15; <100px elenir) önce OCR, çoğu yazı değilse Vision `classify_image` (chart/diagram/form/scan/photo → content_type).
- Vision modeli yokken: tam sayfa/bağımsız görsel → açık hata (`VISION_MODEL ... ekleyin`); metinli sayfadaki gömülü figür → sessizce atlanır, belge ayakta kalır.
- Frontend: JPG/PNG/WebP/BMP kabulü, `<img>` önizleme, Welcome metni güncellendi.
- Doğrulama (container'da gerçek Tesseract + sahte Vision; LLM çağrısı YOK): OCR istatistikleri ✓ · JPG fatura → `ocr_text` (TR-2024-X9 birebir) ✓ · taranmış PDF sayfası → tam sayfa OCR ✓ · grafik + sahte vision → `image_caption` ✓ · vision yok → hata/skip davranışları ✓ · container reload + Vite derleme ✓.

**Adım 5 kod + migrasyon tamamlandı (aynı gün):**
- DB: `documents.summary` (TEXT) + `documents.stats` (JSONB — kimlik kartı: sayfa/chunk/tür dağılımı) + `document_questions` tablosu (id, document_id FK CASCADE, question, position, created_at). `init_db`'ye idempotent ALTER/CREATE eklendi — canlı DB'de doğrulandı.
- `services/summary.py`: başlıklar + stratified örnek (ilk/orta/son, ~2500 karakter) → tek `llm.complete()` çağrısı → JSON parse (code fence/ön-yazı tolere). JSON yoksa/hata varsa `None` (belge embedded kalır).
- `jobs.py`: embed sonrası `stats` kaydı + `asyncio.create_task(_enrich_summary)` — non-blocking; hata belgeyi asla failed yapmaz.
- API: `GET /api/documents/{id}` ve `GET /api/workspaces/{id}` → `summary`, `stats`, `starter_questions`.
- Frontend: `ReadyState` → belge kimlik kartı (sayfa·parça + tür rozetleri) + özet (hazırlanıyor spinner'ı) + 3 tıklanabilir başlangıç sorusu (yalnızca boş sohbette, `messages.length===0`); tıklayınca QA başlar.
- Doğrulamalar: birim (parse/build/generate — LLM mock'lı, gerçek çağrı yok), compile, app import, DB migrasyon canlı, Vite derleme — hepsi OK. Canlı LLM özet çağrısı onay bekliyor.
- Vision canlı testi: `VISION_*` .env'te henüz boş olduğu için yapılamadı; model yazılınca recreate + test edeceğim.

**Adım 6 (UI katmanı) tamamlandı (aynı gün):**
- Güven rozeti UI'ya yansıdı: `AssistantMessage` yanıt altında `Yüksek/Orta/Dolaylı güven · %NN` rozeti (başarısız) — `yetersiz` için badg-error.
- Guardrail red durumu özel kart: kesikli warning çerçeve + shield ikonu "Belgelerde doğrulanabilir bilgi bulunamadı" + neden.
- `App.handleSend`: `meta` dan `rejected`/`confidence`/`confidence_level` yakalanıyor; `error`/`done` mesajına taşınıyor.
- `#page=N` atlama (Adım 1'de hazır): kod tam; tarayıcıda canlı doğrulama kullanıcıda (blob URL fragman davranışı). pdf.js bbox vurgusu kullanıcı kararıyla ertelendi.
- Vite derleme ✓; bu turda hiç LLM çağrısı yok.

**Chunk izlenebilirliği eklendi (aynı gün):**
- `rag.py` meta/done olaylarına `chunk_ids` eklendi — LLM'e giden ilk chunk'ların deterministik id'leri (`<document_id>:<chunk_index>`); reddedilen yanıtlarda `[]`.
- `api/qa.py`: `ChatMessage.citations` artık yapısal nesne: `{sources, chunk_ids, confidence, confidence_level, rejected}` (JSONB, migrasyon yok). Eski satır biçimi frontend'de normalize ediliyor.
- Frontend: rozet yanında **"İncele"** butonu → `InspectModal` popup'ı açar; şimdilik "Adım 1 — İlk retrieve edilen chunk'lar" id listesini gösterir (içerikler sonra çekilecek).
- InspectModal `createPortal(document.body)`'e taşındı (ctx-rise transform'u fixed'ı eziyordu — tam ekran sorunu çözüldü); Reddedilen yanıtlara "Adım 2 — Güvenlik kalkanı" sinyal detayı eklendi (dense/BM25 skor + eşik + geçti/geçmedi).
- Doğrulama: trace mock testi, signals testi, compile, vite, container reload — hepsi tamam.

**Guardrail kalibrasyonu (14.09.2026) — canlı ölçüm:**
- Durum: aynı soru 14:31'de cevaplandı, refactor sonrası `0.72/4.0` eşikleriyle reddedildi (%39). Ölçüm: `text-embedding-3-small` + TR kısa sorgu + 7-chunk korpus → ilgili chunk kosinüsü 0.24–0.42 bandında (alakasız da 0.35–0.43 — mutlak kosinüs ayrıştırmıyor); BM25 ham max ~2.1 (eşik 4.0'a asla ulaşmıyor → sparse kanal ölü).
- Çözüm: eşikler `0.30 / 1.0`'a çekildi (config; `.env` ile değiştirilebilir). Doğrulama: kullanıcının iki gerçek sorusu artık **KABUL** — chunk_ids içinde seri numaralı chunk (7b000a3c:6) var, dense 0.325/0.39 ≥ 0.30, BM25 5.2/3.5 ≥ 1.0.
- **Taviz:** Bu eşiklerle alakasız sorular da genelde geçer → LLM, bağlamda yoksa "belgede bulunmuyor" der (dürüst cevap, maliyet +1 çağrı). Kesin denge TESTING.md'de.

Sırada: Adım 7 (TESTING.md kalibrasyon + arch.md senkronu) + iki canlı doğrulama (vision model set edilince; LLM özet/QA onayınla).

**Workspace düzeyinde özet + başlık eklendi (aynı gün):**
- `documents.summary_status` (pending/done/failed) + `workspaces.summary` + `workspaces.summary_docs` (doc-set imzası) kolonları — idempotent migrasyon (canlı doğrulandı).
- Soru sayısı 1–6: eşik/metrik yok — **LLM karar veriyor** (prompt güncellendi). `document_questions` yapısı aynı; yeniden üretimde eski sorular silinip yenileri yazılıyor.
- Workspace özeti + başlık: doc-set imza + gate — *pending varsa bekle · hiç done yoksa (tümü failed) üretme · failed hariç done özetleriyle sentez* → `workspaces.summary` + `workspaces.name` (LLM başlığı). Tetikleme: her dosya özeti bittikten sonra (2sn drain + lock) ve doküman silinince.
- `qa.py`'deki "ilk soru başlık olsun" fallback'i kaldırıldı.
- Doğrulama: migrasyon canlı, gate probu (legacy belge done sayılır ✓), birim testler (workspace üretimi mock'lu + 1–6 soru), compile, vite, container reload.
- Mevcut workspace'lerin özeti henüz üretilmedi (kredi kuralı) — sıradaki yükleme/silmede otomatik tetiklenir.

**Tablo bağlam satırı eklendi (aynı gün, v1.5-D):** tablo chunk metni `[Tablo: <caption/başlık>]` satırıyla başlıyor (embedding seyrelmesine karşı; Small-to-Big v2'de). `_table_caption` bbox üstü 60pt içindeki kısa bloğu alır, yoksa breadcrumb. Koşul bug'ı (`by0 < tb[1]`) düzeltildi; test yeşil.

**Embedding geçişi: `text-embedding-3-small` → `BAAI/bge-m3` (aynı gün):** dim 1024, chroma/storage/DB temiz sayfa. 1 batch çağrıyla ölçüm: alakalı 0.686 / aynı-belge 0.274 / alakasız 0.248; eskisinde ayrışma yoktu (0.33/0.43). `guard_dense_min` 0.30 → 0.45. Kalibrasyon netliği ciddi arttı — "İncele" modalındaki sinyaller artık gerçekten ayrıştırıyor.

**v1.5 A/B/C tamamlandı (aynı gün):**
- **A — Görsel kırpma:** ≥eşik gömülü görseller `storage/<doc_id>/crops/p<N>_i<M>.png`'e yazılıyor; metadata'ya `image_path`; yeni `GET /api/documents/{did}/crops/{name}` endpoint; silmede otomatik temizlik. UI kısmı (İncele'de figür) ayrı küçük iş.
- **B — Breadcrumb:** `Segment/Chunk.breadcrumbs: list[str]` + chunk metnine `[Bölüm: A > B]` enjeksiyonu (`_with_breadcrumb`); Chroma metadata `breadcrumbs` (JSON) + `section_title`. Non-text türler (tablo/kod/görsel) atomik grup.
- **C — Kod atomik:** monospace (cour/mono/consol) satır bloğu → `content_type=code`, ``` fence'li, bölünmez.
- Doğrulama: host chroma round-trip + container tam çıkarım (kod fence, crop dosyası, breadcrumb) — hepsi yeşil. Compile + import OK.

**Özet hatası görünürlüğü (aynı gün):** `documents.summary_error` kolonu eklendi. `_enrich_summary` başarısızlıkta sebebi kaydediyor (API hatası: `str(exc)` · JSON değil: ham çıktı kesitli · summary boş). `generate_summary` artık JSON değilse `AIError` fırlatıyor (sebeple). API (`summary_status/summary_error`) + UI (kartta kırmızı hata mesajı, sonsuz "hazırlanıyor…" yerine). Not: geçmiş fail'ler için sebep yok — kuzey pdf'sini yeniden tetiklemek **onayınla** (1 LLM çağrısı).

**Kök neden tespit edildi (canlı yeniden test):** birlikte yüklemede `summary_error="LLM servisi boş içerik döndürdü."` — model eş zamanlı 2 çağrıda birine 200 + boş `choices` döndürüyordu (rate-limit/HTTP değil; bu yüzden eski retry'ler kapsamıyordu). Tek yüklemede `done` ✓.

**Çözüm — boş içerik retry'i:** `llm.complete` (özet/workspace), `llm.stream_deltas` (QA) ve `vision.analyze_image` içerik boşsa 3 denemeye kadar yeniden deniyor (aynı backoff); tükenirse `"…boş içerik döndürdü."`. Mock test: boş(2x)→içerik ✓, tükenme→AIError ✓, stream boş→delta ✓, vision ✓.

**Panel servisi kuruldu (aynı gün):** `panel-api` (FastAPI/uv, OKUMA amaçlı — şema/migrasyon yok, web-api yönetir; aynı Postgres + Chroma okur, `chromadb==1.5.9` sabit) ve `panel` (React/Vite/daisyUI). 3 sütun: workspace'ler → dokümanlar → doküman detayı (Süreç: durum/job/progress/özet + Chroma chunk listesi: tür/sayfa/breadcrumb/image_path/metin). Endpoint'ler: `/api/workspaces`, `/api/workspaces/{id}`, `/api/documents/{id}`. Erişim: panel `:5174`, panel-api `:8001` (compose'a eklendi). Canlı doğrulama: 4 workspace + gerçek doküman (kuzey, 11 chunk, job completed dim 1024, `[Bölüm: …]` prefix'li) + vite derleme ✓.



### 15.09.2026

**Rozet koşulu + dense eşik kalibrasyonu:**
- `guard_dense_min` **0.45 → 0.38** (BGE-M3, TR korpus — 0.45 gerçekçi taban aralığının üstünde kalıyordu, 0.35–0.40 bandına çekildi).
- Rozet artık saf kesişim sayısına verilmiyor: kesişen parça `dense ≥ guard_dense_min` VEYA güçlü `BM25 ≥ guard_bm25_min` şartını sağlamıyorsa sayılmıyor (dense skoru görmezden gelinemez).
- Dense katkısız / işi yalnızca BM25 kurtaran cevaplar **%75-80 bandına** sabitlendi: `dense_ok≥2 → %92 yüksek`, `dense_ok==1 → %82 orta`, `bm25_only≥2 → %80 orta`, `bm25_only==1 → %75 dolaylı`, hiçbiri yoksa `%72 dolaylı`.
- İnceleme panelindeki eşikler API'den (`signals.dense_min`) okunduğu için otomatik yansıdı; `rag_arch.md` §C2 senkronlandı.

### 15.09.2026 (robustness paketi)

**A2–A7 güvenlik paketi uygulandı:**
- **Header/footer frekans budaması (#2):** `pdf.py` iki geçişli oldu — ilk geçişte üst/son %10 bandındaki metinlerin sayfalar arası tekrarı sayılır (`header_footer_repeat_ratio=0.6`), tekrar eden (metin, y-bandı) çiftleri `collect_items`'e suppress olarak verilir. Sabit %7 oranının üstüne çift satırlı header sızması da budanıyor; bölüm başlığı gibi sayfa-bazlı değişenler etkilenmiyor.
- **Diyagram bekçisi (#3):** OCR 4 metrik geçse bile `word_count < ocr_diagram_max_words(25) ∧ text_coverage < ocr_diagram_max_coverage(0.15)` ise chunk tipi `image` olur — OCR metni içerik olarak korunur, görsel placeholder ile gösterilebilir, Vision çağrısı yok. `ocr_min_alnum_ratio` **0.70 → 0.75** (rag_arch §2C ile senkron).
- **Tablo bölme (#4):** `table_max_chars=4000` üstündeki tablolar `_split_table` ile satır bazlı bölünüyor; `[Tablo: etiket]` + başlık + ayırıcı her parçada tekrarlanıyor (embed truncate koruması).
- **XY-cut maskeleme (#5):** `order_blocks` artık yalnızca text/code bloklarına uygulanıyor; tablo/görsel `inject_anchors` ile y-merkezine göre sıralı akışa enjekte ediliyor — geniş bloklar sütun kesimlerini bozamıyor.
- **Chroma dimension bekçisi (#6):** "dimension" hatası koleksiyonu resetlemiyor. `embed_dim` + `embed_model` koleksiyon metadata'sına yazılıyor; uyuşmazlıkta açıklayıcı AIError fırlatılıyor (embed job failed + görünür mesaj). `_reset_collection_sync` manuel opsiyon olarak kaldı.

### 15.09.2026 (BM25 stage-1)

**BM25 bellek/senkronizasyon riski giderildi (§3B/C3):**
- **Dirty + revizyon:** `invalidate()` cache'i silmez; `dirty` bayrağı + `_rev` sayacı kurar. Batch upload'lar tek bir arka plan rebuild'ine birleşir.
- **Stale-serve:** `get_index` bayat indeksi anında döndürür, rebuild'i ayrı `asyncio.Task`'ta tetikler → API istekleri rebuild'de asla bloklanmaz.
- **Thread offload:** `BM25Okapi` kurulumu `anyio.to_thread` ile iş parçacığında; event loop diğer isteklerle çalışmaya devam eder.
- **Tek-build garantisi:** per-ws `_build_tasks`; bitmiş ama callback'i bekleyen task'lar yeniden kurulur (yarış düzeltmesi), done-callback kimlik kontrolü (gelecek task'ı düşürme).
- **Konverjans:** build sırasında yeni invalidate olursa revizyon eşleşmez → bayrak yeniden kurulur; bir sonraki sorgu tekrar rebuild eder. Cache yanlış "temiz" işaretlenmez.
- **Soğuk başlangıç:** build await edilir (event loop serbest); hata durumunda hata yeniden fırlatılır — "belge yok" yanıltmacası yok. `clear_workspace()` workspace silmede durum temizler.

Doğrulama: 6 senaryolu async test — soğuk başlangıç, cache hit, stale-serve + arka plan rebuild veri yakalama, build-sırası invalidate konverjansı, done-task yarışı, hata yolu. Hepsi geçti; `app.main` import zinciri temiz.

### 15.09.2026 (equation hattı)

**Blok denklem işleme eklendi (rag_arch ""equation FOLD"" kararı geri alındı):**
- **Tespit** (`services/extract/equations.py` + `blocks.py`): matematik fontu VEYA sembol oranı ≥ %25 (kısa denklem kuralı: ≤12 karakter + ≥1 sembol) + geometri (ortalanma ≥ %15/%85 ya da sondaki (1)/(2.1) numarası). Satır limiti 5, başlık/prose korumaları.
- **Aşama 1 — yerel ($0, ~1ms):** `pylatexenc` (yeni bağımlılık) Unicode'u LaTeX'e çevirir; `\ensuremath{...}` sarmalayıcıları KaTeX dostu komutlara sadeleştirilir; sondaki denklem numarası soyulur; çıktı "yapısal değer" içermiyorsa reddedilir. `$$...$$` olarak chunk'a girer.
- **Aşama 2 — Vision fallback:** yerel başarısız VEYA Office PUA glifleri (U+E000–U+F8FF — OMML kökenli denklemler yerel olarak çözülemez) → bbox kırpımı (200 dpi, 6px nefes payı) → `VISION_PROMPTS["equation"]` ile saf `$$…$$` LaTeX. Vision tanımlı değilse raw Unicode korunur (kırılma yok).
- **Chunk semantiği:** `text` + `equation` segmentleri aynı grupta birleşir → sayfa başına 20 formül = 20 mini chunk olmaz, denklem paragraf bağlamından kopmaz. Saf denklem grubu `content_type=equation`.
- **Tespit zayıflığı düzeltildi:** kısa denklemler (`E = mc²` — sembol oranı %20) yalnızca %25 eşiğiyle yakalanamıyordu; ≤12 karakter + ≥1 sembol kuralı eklendi.

Doğrulama: 10+ birim senaryosu (tespit 7, yerel çevrim, PUA, collect_items, chunk karışımı, hermetik vision fallback, vision-yok) + uçtan uca sentetik PDF (`text → equation → text`), hepsi geçti. `app.main` import zinciri temiz. Not: backend container'da yeni pip paketi (`pylatexenc`) — `docker compose build web-api` gerekli.

### 15.09.2026 (sürekli güven skoru)

**Kesikli rozet merdiveni (92/82/80/75/72) → sürekli 0-100 formül:**
- `confidence_score(top_dense, top_bm25, qualifying, context_k)`: ağırlıklı bileşenler toplamı 100 —
  `58·d + 24·b + 18·c`; `d = norm(top_dense, 0.15→0.70)` (BGE-M3 TR gerçekçi aralık), `b = norm(log1p(bm25), 0→log1p(5))`, `c = kalifiye kesişim / context_k`.
- **Kalifiye kesişim** (eski "dense skoru görmezden gelinemez" kararı korunur): iki kanalda birden geçen ve `dense ≥ 0.38` VEYA `BM25 ≥ 1.0` olan parçalar sayılır.
- **Dense-kör kuralı (eski 75-80 kararının karşılığı):** `d == 0` ve güçlü BM25 (`b ≥ 0.5`) → skor 74-78 bandı;
  zayıf BM25'te 74 tabanı yok (55'e düşer) — guard'ı sınırda geçen sorgular düşük görünür (dürüst).
- **Cevap üretilen sorguda "yetersiz" gösterilmez:** `confidence_min_answered=55` tabanı; seviyeler ≥85 yüksek / ≥65 orta / ≥45 dolaylı / <45 yetersiz.
- **Kalibrasyon (B3):** tüm `CONFIDENCE_*` sabitleri `.env`'den; norm aralıkları ve ağırlıklar kullanıcı loglarındaki false-rejection oranına göre ayarlanabilir. Kullanıcı ekranı senaryosu (dense −0.041, BM25 2.255, 5/5 kesişim) artık **74 orta** — eski 92 yüksek'in aşırı iyimserliği yok; güçlü dense+doyum senaryosu 89 yüksek.

Doğrulama: 7 kalibrasyon senaryosu (kullanıcı ekranı, doyum, çift-güçlü, zayıf, sınırda BM25, orta-düşük) + `app.main` import zinciri — geçti.

### 15.09.2026 (embed görev dayanıklılığı)

**Kök neden (canlı sorun):** `e60329cf` belgesi `pending`'de kaldı, `failed|error=NULL|chunk=0`. Konteyner **22:42:03Z'de yeniden başlamıştı** (upload 22:41:30, ölüm 22:42:13) — in-flight `run_embed_job` görevi kesildi. `asyncio.create_task` fire-and-forget olduğu için hata hiçbir yerde görünmedi; `failed+NULL` = hata-yazma transaksiyonu sırasında torn-write (gerçek başarısızlık değil; chunk=0/progress=0 da hiç ilerlemediğini gösteriyordu). Extract zinciri sağlam — aynı PDF konteyner içinde 33 segment/24 chunk üretti; canlı upload end-to-end embed oldu.

**Düzeltmeler:**
- `jobs/recover.py` (yeni) + `main.py` lifespan: restart sonrası yetim iş taraması — (1) `pending/embedding` + job `pending/running`; (2) torn-write izi: `failed` + `error IS NULL` + `progress=0`. Chroma yarım eklemeleri temizlenir, durumlar sıfırlanır, job yeniden zamanlanır. Yalnızca bu işlem ömründen önce oluşan belgeler (işlem-anı damgası).
- `api/documents.py`: `_spawn_embed_job` — done-callback ile görev hataları artık uvicorn loglarına yazılır (bir daha sessiz hata yok).
- Sonuç: reload'da kurtarma `e60329cf`'i buldu → `pending → embedding → embedded` (30 sn). 9/9 belge embed.

### 15.09.2026 (güven formülü: carrier düzeltmesi)

**Canlı sorgu "unsuz muzlu pankek'in içinde neler var" (e60329cf) incelemesi:**
- Gerçek veriler: dense 0.247 (öğüt: `d = (0.247−0.15)/0.55 = 0.176`), BM25 6.82 (log-doyum → `b=1.0`), uzlaşma **5/5** (`c=1.0`). Eski formül: `58·0.176 + 24·1.0 + 18·1.0 = 52.2` → 55 tabanına çakıldı → "Dolaylı %55". Yani 55 "düşük kanıt" değil, **taban** — dense ağırlığı (58/100) o kadar baskın ki kusursuz BM25 + tam uzlaşma bile 52'yi geçemiyordu; BM25 6.82 ile 1.05 arası fark da log-doyumda sıfırlanıyordu.
- **Taşıyıcı (carrier) modeli:** iki bağımsız yol, her yolun ağırlıkları toplamı 100:
  - dense yolu = `92·d + 8·c`
  - bm25 yolu = `64·b + 28·c + 8·d`
  - `score = max(dense_yolu, bm25_yolu)`; dense-kör + güçlü BM25 taban 74; cevap üreten sorgu taban 55.
- Aynı sorgu şimdi: dense yolu 24.2 / bm25 yolu **93.4** → **93 · yüksek** (konteynerde uçtan uca teyit edildi).
- Regresyon: dense-kör güçlü BM25 → 74 orta ✓; doyum dense → 95 yüksek ✓; zayıf → 55 dolaylı ✓; dense 0 + BM25 4.0 + 5/5 → 85 yüksek ✓ (BM25 tek başına taşıyabilir).
- Ek gözlem (ayrı iş): chunk'ta "MALZEMELER/TARİF" başlıkları ikişer kere tekrarlanmış — layout/heading birleştirme artefaktı; ileride düzeltilebilir.

### 15.09.2026 (BM25 Türkçe tokenizer/kök — canlı kanıtlı)

`bm25.py` yeniden yazıldı — iki düzeltme:
- **Unicode tokenizer:** `[a-z0-9_]+` → `[\w]+` (Python 3 `\w` = Unicode harf/rakam/alt-çizgi). `ç ş ğ ö ü ı` artık token bütünlüğünü koruyor; öncesinde "çıktığında" → `kt`+`nda` diye parçalanıyordu (canlı kanıt: "kabarcıklar çıktığında çevirmelisiniz" → ["kabarc","klar","kt","nda","evirmelisiniz"] idi).
- **Hafif kök eşleşmesi:** sorgu token'inin ilk `stem_min=4` karakteri, indekste aynı ön-ekli terimleri de puanlar (sonek değişkenliği: çevirmeli↔çevirmelisiniz, kabarcık↔kabarcıklar); tam eşleşme baskın, `stem_cap=24` maliyet sınırı. `bm25_index` build artık settings'ten geçirir; göreli import hatası `..core.config` ile düzeltildi.

Canlı doğrulama (kahveli sorgusu, e60329cf): cevap chunk'ı BM25 **0.83 → 5.96** (#1 BM25), qualifying **3/5 → 5/5**, skor **66 orta → 94 yüksek**. "unsuz muzlu pankek" regresyonu **93 yüksek** (değişmedi). Yerel tokenizer/BM25 testleri + `app.main` import temiz. Not: BM25 indeksi bellekte yeniden kurulur — restart sonrası otomatik güncel; veri göçü gerekmez.

### 15.09.2026 (chat geçmişi sayfalama)

**Sınırsız geçmiş → imleç tabanlı sayfalama (en üste kaydırınca eski mesajlar):**
- **Backend** (`api/workspaces.py`): `get_workspace` artık son 10 mesajı + `has_more` döndürür; yeni `GET /{wid}/messages?before_at=ISO&before_id=UUID&limit=N` — `(created_at, id) < (before_at, before_id)` satır-değeri imleciyle eski parti (eşzamanlı kayıtlarda kararlı kırpma, `or_/and_` demeti), `limit` 1-50 arası, dönüş kronolojik. `_message_out` tek şekil (get_workspace iki yerde).
- **Frontend**: `useChatMessages` → `olderAvailable`/`loadingOlder`/`loadOlder(wsId)` (id dedupe + eşzamanlı çağrı koruması `loadingRef` + ağ hatasında otomatik denemeyi durdurur). `ChatMain` scroll kabındadır: `scrollTop ≤ 0` → yükle, tetik anındaki `scrollHeight − scrollTop` "alt çapa"sı saklanıp prepend sonrası geri yüklenir (okuma konumu korunur). Üstte ipucu/spinner. `MessageList` artık yalnızca **en altta yeni mesaj** oluşunca aşağı kayar (stream güncellemesi ve prepend sırasında sürükleme yok).
- Doğrulama: konteyner testi (12 mesajlı workspace: sayfa1=10 has_more=true → sayfa2=2, toplam 12 benzersiz, kronoloji/örtüşmesizlik ✓); `vite build` ✓; `app.main` import ✓.

### 15.09.2026 (LLM/Vision çağrılarında paralellik)

**Sıralı API çağrıları → paralel + ortak eşzamanlılık tavanları:**
- **`vision.analyze_image`**: tüm Vision çağrıları tek küresel `_VISION_SEM` (6) içinde — sayfa görselleri, denklem fallback'i, scanner akışları paralel akar ama sağlayıcıya seri darbe yapmaz; retry'lar da tavana dahil.
- **`equations.vision_fixup`**: sıralı döngü → `asyncio.gather` (sonuçlar item sırasına göre geri atanır).
- **`extract/pdf.py _image_items`**: bir sayfanın gömülü görselleri `gather` ile paralel işlenir (item/düzen sırası sabit); kırpım yazımı sıralı kalır.
- **`embeddings.embed_texts`**: batch'ler `gather` + `_EMBED_SEM` (4) ile paralel; per-batch sıra deterministik (offset'e göre yeniden sıralanır), progress monotonic.
- **`images.process_image`**: Tesseract CPU işidir — `_OCR_SEM` (3) ile sınırlandı (sınırsız paralel OCR thread yarışı engeli); Vision I/O'nun paralelliği korunur.
- Ayarlar: `VISION_MAX_CONCURRENCY`, `EMBED_MAX_CONCURRENCY`, `OCR_MAX_CONCURRENCY` (`.env`).

Doğrulama: hermetik testler — embeddings 250 metin/4 batch `peak=4≤kap` + sıra deterministik; vision_fixup 3 çağrı 65ms'de paralel + sıra korundu; `app.main`/AST temiz. Konteyner uçtan uca: PDF `SEGMENTS 33 / CHUNKS 24` (paralellik öncesiyle aynı). Not: metin LLM üretimi (`stream_deltas`) istek başına tek çağrıdır — paralellik gerektirmez.

### 15.09.2026 (alembic migration + şema sahipliği web-api)

**Alembic entegrasyonu (web-api):**
- `pyproject`'e `alembic>=1.13` + `uv.lock`; dosyalar `web-api/app/alembic.ini` + `web-api/app/alembic/` (env.py async-engine, `%(here)s` script yolu, URL `.env` → env override'ı).
- `0001_initial_baseline` migration elle yazıldı (enum'lar: document_status/embedding_status/chat_role + 5 tablo + index/FK'lar) ve **scratch DB'de `upgrade head` → `alembic check` ile modellerle birebir** doğrulandı ("No new upgrade operations detected").
- Canlı DB (eski create_all+ALTER şeması) **`stamp head` (0001)** ile işaretlendi — veri korundu.
- `core/database.init_db` artık **çalışan migrasyon** değil: tablolar varsa+version yoksa `stamp`, değilse `upgrade`; alembic yoksa (eski imaj) uyarı+devam. `create_all` + ad-hoc ALTER'lar kaldırıldı. Eski "stale job → failed" temizliği migration sonrasına taşındı (recover ile uyumlu).
- Yeni artefakt iş akışı: `cd web-api && .venv/bin/python -m alembic -c app/alembic.ini revision --autogenerate -m "..."` → `upgrade head`.

**Şema sahipliği (panel-api):**
- `panel-api/app/models.py` **silindi** (SQLModel şema aynası kaldırıldı); `sqlmodel` bağımlılığı düşürüldü.
- `core/tables.py` (yeni): tablolar sorgu anında DB'den `autoload` edilir (sync `psycopg` engine, sadece okuma amaçlı; yazma akışı web-api'dedir) — kağıttaki sütun tanımı yok, drift riski yok.
- `api/workspaces.py` + `api/documents.py` Core select'e geçti; panel lise sayımı N+1 → toplu GROUP BY.
- **Build kırığı bulundu & düzeltildi:** `.dockerignore` yoktu → Dockerfile `COPY . .` host `.venv`'ini imaj venv'inin üstüne yazıyordu (`uv run` bozuk venv bulup boşaltıyor → "uvicorn spawn edilemedi", crash-loop). `web-api/`, `panel-api/`, `panel/` için `.dockerignore` eklendi.

Doğrulama: web-api konteyneri (yeni imaj) açılışta migration'ı koşuyor (log'da alembic context), `alembic_version=0001`, API 200; panel-api autoload ile workspace + belge detayı (+Chroma chunk'ları) dönüyor; `alembic check` canlıda temiz.

### 15.09.2026 (print → uvicorn logger)

**Print-tabanlı izler uvicorn logger'ına taşındı:**
- Yeni `core/logging.py`: `get_logger(scope)` → `uvicorn.error.<scope>` kayıtçısı; uvicorn dışında (test/script) kök `basicConfig` fallback'i kurulur (çift basma yok — uvicorn kök handler kurmaz).
- Taşınanlar: `api/documents._spawn_embed_job` (hata → `LOG.error` + traceback via `exc_info`), `jobs/recover` (yeniden deneme hatası → `LOG.warning` + traceback; zamanlanan sayı → `LOG.info`), `core/database.init_db` (şema denetimi/alembic yok → `LOG.warning`; migrasyon hatası → `LOG.error` + `raise`).
- Artık `docker logs`'ta `[uvicorn.error...]` seviyeli ve traceback'li izler; kodda `print()` kalmadı.

### 15.09.2026 (upload ön-doğrulama + docx)

**Uzantı allowlist'i + erken red + ele alma mekanizması:**
- **Allowlist (tek kaynak):** `extract/constants.SUPPORTED_EXTS = .pdf .docx .txt .md .png .jpg .jpeg .webp` (bmp/tif/tiff çıkarıldı). `api/documents.upload_document` gövde akışından ÖNCE `415` ile reddeder; 25MB üstü `413` (mevcut). Frontend `ACCEPTED_FILE_ATTR` senkronu.
- **Ele alma mekanizması:** `extract/__init__` if/elif zinciri → **`_HANDLERS` kaydı** (uzantı → işleyici). Yeni tür = yeni handler + kayıt; hepsi asenkron, imza `(content, crop_dir=None)`.
- **DOCX desteği (yeni):** `extract/docx.py` — bağımlılıksız `zipfile`+`ElementTree` ile `word/document.xml` paragraf metinleri → tek `text` Segment. PDF/görsel/metin yolları korundu.

Doğrulama: birim (docx çıkarımı, md rotası, desteklenmeyen uzantı hatası+allowlist, küme eşitliği) ✓; canlı API: `.exe` → 415 (gövde okunmadan), `.docx` → 200 pending ✓; `app.main`/vite build temiz.

### 15.09.2026 (InspectModal: chunk içerikleri)

**"Yakında" placeholder'ı → gerçek chunk içerikleri:**
- **Backend:** `chroma_store.get_chunks_by_ids(ids)` (Chroma `get(ids=...)` + `parse_get_row` — artık `page_context/breadcrumbs/section_title/image_kind` de taşır); yeni `GET /api/chunks?ids=doc:idx,doc:idx` (1-20 kimlik, 422 sınır; bulunamayan göz ardı edilir, `found` sayısı döner).
- **Frontend:** `chunksAction(ids)`; InspectModal "Adım 3 — Chunk içerikleri": her chunk için kart (belge adı, parça no, sayfa, `content_type` rozeti, bölüm başlığı, `image_path` rozeti) + `max-h-48` kaydırılabilir metin bloğu. Yükleme spinner'ı, hata durumu, silinmiş chunk için "bulunamadı" göstergesi; `chunkIds` değişmedikçe yeniden çekilmez (iptal edilebilir effect).

Doğrulama: canlı `GET /api/chunks` (2/2 bulundu, metin+tip+sayfa ✓); `app.main` + `vite build` temiz.

### 15.09.2026 (markdown/KaTeX + dosya parçalama)

**#11 — Ayrıştırıcı sağlamlaştırma + denklem render:**
- `lib/markdown.js` yeniden yazıldı: **özyinelemeli** satır içi ayrıştırma (kalın/italik İÇİNDE atıf ve matematik çözülür), `$$…$$` blok / `$…$` satır içi matematik, `[Görsel: …]`, atıf, kod; döviz kalıpları (`$5,00`) matematik sanılmaz (`MATH_HINT`); **iç içe liste** (girinti derinliği) ve liste/paragraf ayrımı.
- `RichText.jsx`: düğüm ağacı render'ı + **KaTeX** (`katex`, `throwOnError:false`; hata halinde ham metin), blok denklem `displayMode`; `main.jsx`'e `katex.min.css`. Nested liste render'ı.
- Doğrulama: 7 senaryolu node birim testi (özyinelemeli atıf, blok/satır içi matematik, döviz negatifi, görsel, iç içe liste, karışık liste+paragraf, çit+başlık) ✓; `vite build` (KaTeX dahil) ✓. Not: paket boyutu +~260KB (gzip +80KB) — gerekirse lazy import.

**#13 — Dosya parçalama:**
- `App.jsx` (229 satır) → iskelet `App.jsx` (~120) + **`hooks/useAppState.js`** (~170): route/yaşam döngüsü, workspace açma, sohbet, dosya seçimi, modal durumu, türevler tek yerde.
- `markdown.js` ve `RichText.jsx` yeni ayrıştırıcı/render katmanına göre yeniden sınırlandı (parser ↔ renderer ayrımı net).
- `useAttachments` olduğu gibi (157) — büyüme noktası artık izole hook; ileride `useChatMessages` deseniyle ayrılabilir.

### 15.09.2026 (bloklayıcı I-O → thread)

**Event loop dışına taşınan dosya işlemleri (`core/fs.py`):**
- `rmtree_ignore`, `write_bytes`, `read_bytes` — hepsi `anyio.to_thread` içinde (BM25 rebuild deseniyle tutarlı, döngü kilitlenmez).
- 7 çağrı yeri güncellendi: embed iptal temizliği, workspace/belge silme (3), upload-abort, crop `write_bytes` (pdf), extract `read_bytes`.
- Kullanılmayan `import shutil`'lar kaldırıldı.

Doğrulama: canlı döngü upload(PDF)→embedded(2s)→delete→depo temiz ✓ (extract read/crop write/silme thread'li çalışıyor); AST + `app.main` temiz.

### 15.09.2026 (atıf etiketi regresyonu düzeltildi)

**Belirti:** kaynaklarda artık yalnızca belge adı görünüyordu ("hangi chunk'tan yararlandığı" kayboldu).

**Kök neden:** markdown yeni ayrıştırıcısında `CitationBadge`'e verilen `label` değişmişti — eski: `p.slice(1,-1)` (tam `"Belge, sayfa N, parça M"`); yeni: `m[1].trim()` (yalnız belge adı). Badge görünür metni `label`ı bastığı için sayfa/parça yalnız tooltip'te kaldı.

**Düzeltme (`lib/markdown.js`):** `label` tam köşeli metne döndü; tıklama (önizleme sayfa/parça atlama) için `filename` ayrıca `m[1]`den tutuluyor. `[Belge: …]`/`[Kaynak: …]` ön ekli varyantlar da tam etiketle çözülüyor. Doğrulama: node birim testi + `vite build` ✓.

### 15.09.2026 (ARQ iş kuyruğu — embed yerine ayrı worker süreci)

**İş yürütme modeli değişti (`asyncio.create_task` → Redis kuyruğu + ayrı worker):**
- **Redis** servisi (compose, healthcheck) + **`web-worker`** servisi (aynı web-api imajı, `arq app.worker_settings.settings` ile çalışır — 3 görev: `embed_document`, `enrich_document`, `workspace_summary`; `max_jobs=4`, `job_timeout=1800`, `max_tries=3`, `retry_jobs`, keep_result=0).
- **`core/taskq.py`**: `RedisSettings.from_dsn(redis_url)` pool + `enqueue(name, *args, _defer_by=…)` — web-api görev üretir, worker tüketir; redis yoksa hata → log + belge pending'de kalır (boot'ta recover kuyruğa yeniden atar, idempotent).
- **`worker_runners.py`** (görev sarmalayıcıları) + **`worker_settings.py`** (arq 0.28 `func()` sözlük ayarları).
- **Katkılar:** `jobs/embed.run_embed_job` artık worker sürecinde; sonunda `enrich_document` **enqueue** eder (create_task kalmadı). `jobs/enrich` refactor: `enrich_document(ws, doc)` chunk'ları Chroma'dan yeniden okur (kuyruk dayanıklılığı), `schedule_workspace_summary` → `_defer_by=2` ile kuyruğa. `api/documents.upload` → `enqueue("embed_document", …)`; `recover_orphaned_jobs` → create_task yerine enqueue. `chroma_store.get_chunks_by_document`.
- **Config:** `redis_url` (.env).
- +++ Worker'ın görev süresi/başarısı `arq` loglarında görünür (`1.85s ← embed_document ● 'ok'`); görev yeniden deneme arq katmanında (retry_jobs).

Doğrulama: compose config ✓; worker "3 functions" ile ayağa kalktı; uçtan uca PDF yükleme → worker `embed_document` 1.85s ok → otomatik `enrich_document` → `embedded`; silme ✓. Not: CP210 — yeni pip paketi (arq) için `docker compose up -d --build web-api web-worker redis` gerekli.

### 15.09.2026 (embed akışlı yazma + idempotent upsert)

**Bellek sınırı / adım-adım vektör yazma:**
- **`embeddings.embed_batches`** (yeni): batch'ler paralel çekilir, her tamamlanan batch `on_batch(offset, vectors)` ile **akışla** teslim edilir — tüm vektör matrisi RAM'de birikmez. `embed_texts` (sorgu vektörü kullanımı) bu akışı toplayan ince sarmalayıcı oldu (deterministik sıra korunur).
- **`chroma_store.upsert_chunks`** (yeni): `add` yerine **`upsert`** — aynı id üzerine tekrar yazılabilir (ARQ retry_jobs ile mükemmel uyum: yarıda kalan iş yeniden çalıştırıldığında çakışma yok); vektörler numpy olarak geçilir (`tolist()` kopyası yok). Eski `_add_sync`/`add` kaldırıldı.
- **`jobs/embed`**: `embed_texts+add` yerine `embed_batches(on_batch=write_batch)` — her 64'lük batch biter bitmez Chroma'ya yazılır; uyarı eşiği `embed_memory_warning_chunks=2000` (aşınca LOG.warning); dim ilk batch'ten alınır; `bm25_index.invalidate` tüm yazım sonunda bir kez.
- Canlı: tek PDF → worker `embed_document` 1.98s ok → `embedded` (upsert yolu) → silme ✓. Not: worker kod değişikliklerinde `docker compose restart web-worker` gerekir (arq reload'u yok).

### 15.09.2026 (DENSE KÖK NEDEN: Chroma uzayı L2 idi + temizlik)

**Belirti:** Dense kosinüs hep düşük/negatif, eşik asla geçmiyor.
**Kök neden:** Chroma koleksiyonu **`hnsw.space='l2'`** ile yaratılmış (eski kurulum); `get_or_create_collection` mevcut koleksiyona cosine metadata'sını uygulamıyor. `parse_query_row` skoru `1 − distance` hesapladığından L2² için negatif çöp üretiyordu (kanıt: dist=1.3282=L2², gerçek cos=+0.3359). Dense kanal fiilen ölüydü.
**Düzeltmeler:**
- `chroma_store._col()` uzay bekçisi: `l2` ise koleksiyonu **cosine ile yeniden yaratır** (uyarı loglar); deadlock'suz `_recreate_collection_locked`.
- **Embed ↔ gösterim ayrımı:** `Chunk.embed_text` (breadcrumb ön eki YOK) → Chroma `documents`/BM25 bu metni kullanır; LLM bağlamı `[Bölüm: …]`'ı `breadcrumbs` metadata'sından yeniden kurar (görsel/içerik kaybı yok).
- **Temizlik:** `normalize_text` → satır-sonu tireleme birleştirme + ok/glif (`➨➔→`) temizliği; `emit_segments` başlık temizliği + ardışık tekrar dedupe.
- Koleksiyon yeniden embed edildi (10 belge): `space=cosine`, 160 chunk; skorlar **+0.31…+0.34** (gerçek kosinüs).
- `guard_dense_min` **0.38 → 0.30** (ölçülen gerçekçi bant; InspectModal eşiği API'den okur).
**Kalan (P1):** chunk konu sınırı — epirojenez cümlesi hâlâ "Aşındırma Platoları" chunk'ının kuyruğunda (başlık tespiti kaçırıyor) → heading tabanlı bölme iyileştirmesi.

### 15.09.2026 (P1: başlık tabanlı konu sınırı)

**Belirti:** epirojenez cümlesi "Aşındırma Platoları" chunk'ının kuyruğunda kalıyordu (chunk konuları karışıyordu).

**Düzeltme (`extract/blocks.py` + `layout.py`):**
- `blocks._text_item` artık metin item'ına **satır bilgisi** taşır (`lines: [{text,size,bold}]`).
- `emit_segments` metin item'larını **satır satır** işler; orta-blok başlık benzeri satır breadcrumb'ı güncelleyip **konu sınırı çizer**: font kuralı VEYA `Epirojenez:` (iki-nokta bitişli) VEYA caption kalıbı `Başlık: gövde…` (kısa ön ek + satır başı büyük harf). Aynı boyutlu yeni başlık kardeş bölüm sayılır (yığmaz, değiştirir).
- Sonuç: her konu kendi segmentine/`page_context`'ine → chunk ayrımı konu bazlı.

**Doğrulama:** birim (orta-blok başlık → iki segment, ctx güncellenir) ✓; yalnızca ölçüm workspace'i (37eee3fd) yeniden embed edildi:

| | Önce | Sonra |
|---|---|---|
| epirojenez chunk rank | 2/18 | **1/19** |
| soru↔chunk kosinüs | 0.3227 | **+0.3871** |
| dense eşiği (0.30) | geçmezdi | **geçiyor** |

Arka plan notu: bu oturumda dense iyileştirme zinciri bütünleşti — (1) Chroma uzayı L2→cosine düzeltmesi, (2) embed↔gösterim ayrımı (`embed_text`), (3) sembol/tire/başlık temizliği, (4) başlık-tabanlı konu sınırı, (5) eşik kalibrasyonu 0.30.

### 15.09.2026 (P1: liste/madde öğeleri ayrı chunk'a bölünüyordu)

**Belirti:** "Depremin Az Olduğu Alanlar:" başlığından sonraki 4 madde (ve `➨` öğeli diğer listeler) her satır ayrı chunk + ayrı `section_title` olarak düşüyordu (canlı: folyo-gorsel-test.pdf sayfa 2, eski chunk #13-17). Satır aralarındaki yalnız `➨` satırları da ayrı boş chunk'lar üretiyordu.

**Kök neden:** Sayfa 2'de gövde 9px, liste öğeleri 12px (kaynak düzeninde liste stili gövdeden büyük). `threshold = max(body×1.15, body+1) = 10.35` olduğundan **font kuralı her 12px'lik madde satırını başlık sanıyordu** → `push_heading` aynı boyut ailesinde breadcrumb'ı sürekli değiştiriyor → her satır farklı `page_context` → `chunk_segments` birleştiremiyor → satır satır chunk.

**Düzeltme (`extract/layout.py`):**
- `_is_list_item(text)`: satır başı işaretçilerini tanır — ok/glif öğeleri (`➨➔→`), madde işaretleri (`•·∙◦○●◉■▪‣➢`), çizgiler (`- – —` + boşluk), `*`/`+`, numaralar (`1.`, `1)`, `(1)`).
- `is_heading_line` başında list kontrolü: madde öğesi **asla başlık değildir** → tek tema altında tek chunk'ta birleşir; yalnız `➨` satırları da (temiz hali boş) başlık olmaz.
- Roman rakamlı bölüm başlıkları (`I. ARNAVUTKALDIRIMI…`) etkilenmez (sadece `\d`), `Epirojenez:` iki-nokta kuralı ve caption kuralı korunur.

**Doğrulama (folyo-gorsel-test.pdf):**
- Önce: sayfa 2 madde listeleri satır satır chunk (13-18 arası 6 ayrı chunk).
- Sonra: "Depremin Az Olduğu Alanlar:" + 5 madde → **tek chunk**; "Türkiye'deki Fay Hatları:" + KAF/DAF/BAF → tek chunk; yalnız `➨` segmentleri kayboldu (73→61 segment).
- Regresyon: kuzey_ruzgari-v2 80 segment/11 chunk değişmedi; sentetik alt-yazı senaryosu 6→2 chunk; diğer PDF'ler hatasız.

### 15.09.2026 (Görsel kaynak gösterimi: tip bilgili tek seferlik block görsel)

**Belirti:** Chat cevabında görsel tipindeki chunk (ör. parça 9) normal metin atıfıyla `[Belge, sayfa N, parça M]` rozetine dönüşüyor, `[Görsel: …]` block görseli hiç çizilmiyordu; model görselden beslenen her bilgiyi ayrı atıflamaya eğilimliydi.

**Karar (kullanıcı):** Kaynak gösterimi tip-bilinçli — metin/denklem tipi → mevcut satır içi `[Belge, sayfa N, parça M]` rozeti (her kullanımda); görsel tipi → `[Görsel: belge_id/dosya_adı]` **block görsel**, cevapta YALNIZCA bir kez, en alakalı noktada. Görsel için ayrıca metin atıfı/`görsel:` etiketi yazılmaz. Frontend `[Görsel: …]`'i zaten `block` `<img>` olarak çiziyor → UI değişikliği gerekmedi.

**Uygulama:**
- `prompts.py` kural 6: görsel-tipi kaynak = künyede `görsel:` alanı olan parça; `[Görsel: …]` tek kez, block görsel, ek metin atıfı yok, `görsel:` etiketi çıktıya kopyalanmaz; aynı `görsel:` değerli birden çok parça tek kaynaktır.
- Kural 7: `görsel:` alanı OLMAYAN kaynaklar (metin, denklem) normal satır içi atıf, tekrarlanabilir; alt tarafta liste yok.
- `llm._user_content`: "KULLANILABİLİR GÖRSELLER" notu yenilendi — tek nokta, tek yer tutucu, görsel için `[Belge, sayfa, parça]` atıfı yok.

**Tip taşıma:** `_context_label` görsel parçalarına `görsel:` alanı koyar (tip + kimlik), metin parçalarında bu alan yoktur → tip LLM'e gider, cevaba "tip:" olarak sızmaz.

### 15.09.2026 (P0: "Yanıt alınırken bir hata oluştu." — QA sessiz patlıyordu)

**Belirti:** Belge yüklenip embedlendikten sonra sorulan sorulara web-api boş SSE (200 + 0 byte) dönüyor; UI "Yanıt alınırken bir hata oluştu." gösteriyor. İnline test (`uv run python`) hep çalışıyor, web-api restart'ı iyileştiriyor.

**Kök neden:** Chroma **SQLite** (`chroma.sqlite3`) dosya tabanlı; **web-api ve web-worker aynı dosyaya erişen iki ayrı süreç**. Uzun ayakta kalan api sürecindeki `chromadb.PersistentClient`, worker'ın (yeni belge embed'i) yazmasından sonra bayatlıyor → `_query_sync`/`get` anında hata → `qa.py gen()` exception'ı **sessizce yutuyordu** (traceback yok) → boş akış → genel hata. Taze süreç = taze istemci → hep çalışıyor; restart = iyileşme. Deliller: başarısız pencerede yalnızca yeni embedlenen workspace sorguları bozuk, 832ms'de boş body, restart sonrası düzeliyor.

**Düzeltmeler:**
- `api/qa.py`: sessiz yutma kaldırıldı — `error` event `LOG.warning`, exception `LOG.exception` (bir sonraki tekrarında tam traceback log'a düşer); hata mesajı DB yazımı da ayrı try/catch'ta loglanır.
- `services/chroma_store.py`: **kendi kendini iyileştirme** — `_reset_client()` istemci/collection singleton'ını sıfırlar; `_run_with_reopen_retry()` tüm chroma okuma/yazma işlemlerini sarar: Chroma hatasında istemciyi yeniden açıp 3 denemeye kadar tekrarlar (geçici `database is locked` için kademeli bekleme); boyut uyuşmazlığı (`AIError`) tanısal olduğundan denenmez.

**Doğrulama:** kullanıcının workspace'i (ad9a19b9) üzerinden direct + caddy yolları: meta+delta+done, cevap DB'ye gerçek metin olarak yazıldı (16:45 mesajları).

**Kalıcı mimari not:** asıl çözüm tek yazarlı erişim (Chroma'yi HTTP/single-writer moduna almak) — bu yama o güne kadar api'yi restart'sız kurtarır.

### 15.09.2026 (Özet hatası: "Özet yanıtı JSON değil" — kırık JSON'a çok katmanlı onarım + retry)

**Belirti:** Belge özetleri `summary_status=failed` + "Özet yanıtı JSON değil: '{"summary": …'" — model özet metninin içine kaçışsız `"` koyunca (veya çit/ön-yazı/kuyruk çöpü üretince) tek stratejili `parse_json_blocks` patlıyordu; workspace özetleri de sessizce None'a düşüyordu.

**Düzeltme (`services/summary.py`):**
- `parse_json_blocks` çok katmanlı: (1) fence/ön-yazı temizliği + `{…}` bölgesi `json.loads`, (2) `JSONDecoder.raw_decode` — kuyruk çöpüne rağmen ilk geçerli nesne, (3) `ast.literal_eval` — Python tarzı tek tırnaklı çıktı, (4) `allow_salvage` ile alan-bazlı regex kurtarma (`summary`/`title`/`questions` — kısmi ama kullanılabilir).
- `generate_summary`/`generate_workspace`: **ilk deneme sıkı** (`allow_salvage=False`); kırıksa tek katı yeniden deneme (`_strict_nudge` mesajı, temperature 0.5); o da kırıksa salvage kabul. Böylece kısmi kabul yerine önce temiz JSON denenir.

**Doğrulama (canlı):** 6 zorlu girdi testi (kaçışsız tırnak, fence, ön/art yazı, tek tırnak, kuyruk çöpü, tam kırık) — hepsi kurtarıldı; worker restart + 5 `enrich_document` yeniden tetiklendi → **13/13 belge done, 0 failed**; workspace başlığı ("Türkiye'de Platolar ve Deprem Fay Hatları") ve özetleri üretildi.

### 15.09.2026 (Frontend: XHR→fetch + React projeleri TypeScript'e)

- **XHR kaldırıldı:** `uploadDocumentXHRAction` → `uploadDocumentAction` (modern `fetch`). Fetch'in upload ilerlemesi olmadığından FileBar `%` yerine belirsiz "yükleniyor…" gösterir; iptal handle'ları (abort) kaldırıldı.
- **web + panel TypeScript:** tüm `src` `.jsx→.tsx`, `.js→.ts`; `tsconfig.json` (strict, bundler), `vite-env.d.ts`; tipli prop'lar, API yanıt tipleri (`Workspace/Document/Chunk/ChatMessage/QaEventMap`), markdown düğüm ağacı tipleri (`InlineNode/Block/ListBlock`), zustand store typing, `npm run typecheck` (`tsc --noEmit`).
- `web/panel/.env` → `VITE_API_BASE_URL` (aynı-origin `/api` varsayılan; gitignore'da, `.env.example` commit'te).
- Doğrulama: her iki uygulama `tsc --noEmit` temiz; prod Docker build (Vite build + Caddy) başarılı; statik 200 + `/api` proxy smoke testi geçti.
