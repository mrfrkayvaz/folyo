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


