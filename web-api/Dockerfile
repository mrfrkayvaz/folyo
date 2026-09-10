# --- uv tabanlı FastAPI image ---
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

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]