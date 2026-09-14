from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = ""
    chroma_dir: str = "chroma_data"
    # Uzaktan chroma server (bağımsız servis — HTTP). Boşsa hata verilir.
    chroma_host: str = ""
    chroma_port: int = 8000
    # Panel API taşıyıcı (bearer) token imzası — HMAC anahtarı.
    # Prod'da (Coolify) AUTH_SECRET set edilmeli; boşsa dev fallback'i kullanılır.
    auth_secret: str = ""
    auth_token_ttl_hours: int = 24
    # Admin seed: `python -m app.seed_admin` bu hesabı users tablosuna idempotent ekler.
    admin_username: str = ""
    admin_password: str = ""
    # Dev CORS: virgülle ayrılmış origin listesi (boşsa CORS middleware eklenmez).
    # Prod'da frontend aynı-origin /api kullandığından genelde gerekmez.
    cors_origins: str = (
        "http://localhost:5173,http://localhost:5174,http://localhost:8080,http://localhost:8081"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()