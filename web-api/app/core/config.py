from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""

    embed_api_key: str = ""
    embed_base_url: str = ""
    embed_model: str = ""

    database_url: str = ""
    chroma_dir: str = "chroma_data"
    storage_dir: str = "storage"

    chunk_chars: int = 900
    chunk_overlap: int = 120
    top_k: int = 6
    similarity_threshold: float = 0.3
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
