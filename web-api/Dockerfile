# --- uv tabanlı FastAPI image (production / Coolify) — KÖK build context ---
# (shared/ paketini de imaja alır; dockerfile: web-api/Dockerfile, context: repo kökü)
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Bağımlılıkları lockfile'dan kur (katman önbelleği için önce kopyala)
COPY web-api/pyproject.toml web-api/uv.lock ./
RUN uv sync --frozen --no-dev

# Uygulama + ortak (shared) kodu
COPY web-api/app ./app
COPY shared ./shared

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Kalıcı veri (Coolify'da volume bağla): Chroma vektör DB + yüklenen belgeler
VOLUME /app/chroma_data /app/storage

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"

CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
