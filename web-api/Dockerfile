# --- uv tabanlı FastAPI image (production / Coolify) ---
# Aynı imaj, web-worker (ARQ) için de kullanılabilir:
#   komut override → "uv run --no-sync arq app.worker_settings.settings"
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# OCR sistem bağımlılıkları (Tesseract + Türkçe/İngilizce dil verisi)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-tur tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Bağımlılıkları lockfile'dan kur (kaynak kopyalamadan önce — katman önbelleği için)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Uygulama kodunu kopyala
COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Kalıcı veri (Coolify'da volume bağla): Chroma vektör DB + yüklenen belgeler
VOLUME /app/chroma_data /app/storage

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"

CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]