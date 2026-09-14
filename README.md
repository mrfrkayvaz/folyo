# Folyo — Belge Analiz ve Soru-Cevap Sistemi

Folyo, yüklenen belgeler üzerinden doğal dilde soru sorulabilen bir RAG sistemidir. PDF, TXT, MD ve görsel dosyaları işler. Yanıtlar, bilginin kaynağını gösteren satır içi atıflar ve bir güven skoruyla döner; belgelerde yeterli bilgi yoksa LLM çağrısı yapılmaz ve "bilgi bulunamadı" mesajı gösterilir.

Sistem hazır bir RAG kütüphanesi kullanılmadan sıfırdan yazılmıştır; kararların gerekçeleri ve geliştirme yolculuğu "Ek dokümanlar" bölümünde.

## Nasıl çalışıyor

1. Dosya önce `storage/`'a kaydedilir, sonra Redis üzerindeki ARQ kuyruğuna `embed_document` görevi bırakılır. Görevi ayrı bir süreç olan worker tüketir.
2. Worker içeriği çıkarır, görsellerde OCR sonrası gerekirse görsel modeli devreye sokar, metni parçalara böler, vektöre çevirip Chroma'ya yazar.
3. Embed sonrası belge için özet ve başlangıç soruları üretilir; workspace için de ortak bir özet ve başlık çıkarılır.
4. Soru sorulunca vektör benzerliği ve BM25 olmak üzere iki kanal ayrı çalışır. Sonuçlar RRF ile birleştirilir, eşik kontrolünden geçer ve en alakalı parçalar LLM'e bağlam olarak verilir. Cevap akış halinde döner ve kaynaklarıyla birlikte kaydedilir.

## Servisler ve portlar

| Servis | Rol | Port |
|---|---|---|
| `web` | Kullanıcı arayüzü | 5173 |
| `caddy` | Ters proxy | 8080 |
| `web-api` | API | 8000 |
| `web-worker` | Kuyruk işçisi | — |
| `panel-api` | Yönetim API'si | 8001 |
| `panel` | Yönetim paneli | 5174 |
| `chroma` | Vektör veritabanı | 8002 |
| `redis` | Kuyruk | — |
| `db` | PostgreSQL | 5432 |

Panel, embed süreçlerini, özetleri ve Chroma parçalarını izlemek içindir.

## Çalıştırma

### Gereksinimler

Docker ve Docker Compose v2.

### 1. Ortam değişkenleri

`.env` dosyalarını örneklerden kopyalayıp doldurun:

```bash
cp web-api/.env.example web-api/.env
cp worker/.env.example worker/.env
cp panel-api/.env.example panel-api/.env
```

- `web-api/.env` ve `worker/.env`: LLM, embedding ve görsel model anahtarları. Her biri OpenAI uyumlu bir API adresi ve anahtar ister; `EMBED_MODEL` ve `VISION_MODEL` dolu olmalı.
- `panel-api/.env`: `ADMIN_USERNAME` ve `ADMIN_PASSWORD`. Sisteme giriş yapacak admin hesabı.

`DATABASE_URL`, `REDIS_URL` ve `CHROMA_HOST` adresleri compose içinde zaten tanımlıdır; `.env`'de doldurmaya gerek yoktur. Yalnız Docker dışında çalışacaksanız gerekir.

Not: VISION anahtarı olmadan sistem kalkar; yalnızca OCR'ın yetmediği görsel belgeler hata verir. LLM ve embedding anahtarları olmadan ise çalışmaz.

### 2. Ayağa kaldırma

```bash
docker compose up -d --build
```

### 3. Admin kullanıcısını oluşturma

```bash
docker compose exec panel-api uv run --no-sync python -m app.seed_admin
```

İdempotenttir; admin kullanıcısı zaten varsa bir şey yapmaz. Veritabanı şeması ilk açılışta alembic ile kurulur.

### 4. Erişim

- Kullanıcı arayüzü: http://localhost:5173 veya http://localhost:8080
- Yönetim paneli: http://localhost:5174
- API durumu: http://localhost:8000/api/health

Her iki arayüz de admin hesabıyla giriş ister.

## Günlük kullanım

1. Yeni bir sohbet açın.
2. Dosya yükleyin. Tek dosya 25 MB sınırının altında olmalı; desteklenmeyen uzantı reddedilir.
3. İşlenmesini bekleyin; özet ve önerilen sorular görünür.
4. Soru sorun. Cevaptaki `[Belge, sayfa N, parça M]` etiketleri tıklanabilir; "İncele" ile cevabın dayandığı parçalar açılır.

## Bakım

```bash
# Yeni npm paketi eklendi
docker compose up -d --build web panel

# Yeni Python bağımlılığı eklendi
docker compose build web-api web-worker panel-api

# .env değişti
docker compose up -d --force-recreate web-api web-worker panel-api

# Worker kodu değişti
docker compose restart web-worker

# Loglar
docker compose logs -f web-api web-worker panel-api
```

Veriler: belgeler `storage/`, vektörler `chroma_data/`, PostgreSQL verisi `pgdata` volume'unda tutulur. `docker compose down -v` yalnızca PostgreSQL verisini siler; `storage/` ve `chroma_data/` kalır.

## Testler

```bash
scripts/test.sh
```

Beş suite çalıştırır: shared + web-api, panel-api, worker ve iki React projesi.

## Klasör yapısı

```
web/           kullanıcı arayüzü (React + Vite + TypeScript)
web-api/       kullanıcı API'si (FastAPI)
panel/         yönetim paneli (React + Vite + TypeScript)
panel-api/     yönetim API'si (FastAPI; alembic ve admin seed burada)
worker/        kuyruk işçisi (extract, OCR, vision, chunk, embed, özet)
shared/        ortak katman (modeller, chroma/bm25/embed servisleri)
chroma/        Chroma görüntü yapılandırması
storage/       yüklenen belgeler ve kırpımlar
chroma_data/   vektör verisi
tests/         ortak ve Python testleri
scripts/       geliştirme ve test betikleri
```

## Ek dokümanlar

- `arch.md` — mimari kararlar
- `rag_arch.md` — kesin mimari
- `DEVLOG.md` — geliştirme yolculuğu