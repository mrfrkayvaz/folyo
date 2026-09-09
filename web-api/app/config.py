"""Ortam ayarları — web-api/.env dosyasından okunur (CWD = web-api iken).

Boş bırakılan alanları sen doldur; kod anahtar/URL eksikse anlaşılır hata döner.
Varsayılan modeller senin seçimin: Nemotron 3 Ultra (LLM) + Nemotron 3 Embed 1B (embedding).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── LLM (soru-cevap üretimi) ───────────────────────────────────────────────────
    llm_api_key: str = ""        # .env: LLM_API_KEY (zorunlu)
    llm_base_url: str = ""       # .env: LLM_BASE_URL (zorunlu)
    llm_model: str = ""          # .env: LLM_MODEL — varsayılan yok, sadece .env'den okunur

    # ── Embedding ───────────────────────────────────────────────────────────────────
    embed_api_key: str = ""      # boşsa LLM_API_KEY kullanılır
    embed_base_url: str = ""     # boşsa LLM_BASE_URL kullanılır
    embed_model: str = ""        # .env: EMBED_MODEL — varsayılan yok, sadece .env'den okunur

    # ── Veritabanı & depolama ─────────────────────────────────────────────────────────
    database_url: str = ""       # .env: DATABASE_URL (postgresql+asyncpg://...)
    chroma_dir: str = "chroma_data"
    storage_dir: str = "storage"

    # ── RAG parametreleri ───────────────────────────────────────────────────────
    chunk_chars: int = 900
    chunk_overlap: int = 120
    top_k: int = 6
    temperature: float = 0.2
    data_dir: str = ".ragdata"

    @property
    def llm_ready(self) -> bool:
        return bool(self.llm_api_key and self.llm_base_url)

    @property
    def embed_ready(self) -> bool:
        return bool((self.embed_api_key or self.llm_api_key) and (self.embed_base_url or self.llm_base_url))


@lru_cache
def get_settings() -> Settings:
    return Settings()
