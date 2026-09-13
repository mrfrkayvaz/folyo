# Folyo ARQ Worker — bağımsız servis (worker_app paketi)
#
# Build context = REPO KÖKÜ; imaj YALNIZCA worker kodunu içerir (web-api'den
# hiçbir import yok — tanımlar worker_app altında yerel kopyalardır).
#   docker compose build web-worker      (build: { context: ., dockerfile: worker/Dockerfile })
#
# Dev'de compose bind-mount'u (./worker/worker_app) canlı kodu ezer;
# prod'da (Coolify) imaj tek başına çalışmaya yeter.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# OCR sistem bağımlılıkları (taranmış sayfa fallback'i için)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-tur tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Worker bağımlılıkları (lockfile'dan; katman önbelleği için önce kopyala)
COPY worker/pyproject.toml worker/uv.lock ./
RUN uv sync --frozen --no-dev

# Worker kodu + ortak (shared) — çalışma hattı worker_app'ta, ortak tanımlar shared/ altında.
COPY worker/worker_app ./worker_app
COPY shared ./shared

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Kalıcı veri (Coolify'da volume bağla): Chroma vektör DB + yüklenen belgeler
VOLUME /app/chroma_data /app/storage

# ARQ worker: görevleri (embed/enrich/workspace_summary) Redis kuyruğundan tüketir.
CMD ["uv", "run", "--no-sync", "arq", "worker_app.worker_settings.settings"]