# uv tabanlı FastAPI imajı — panel-api (production / Coolify) — KÖK build context
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY panel-api/pyproject.toml panel-api/uv.lock ./
RUN uv sync --frozen --no-dev

COPY panel-api/app ./app
COPY shared ./shared

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Chroma verisini okuma amaçlı erişim (Coolify'da volume bağla)
VOLUME /app/chroma_data

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"

CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
