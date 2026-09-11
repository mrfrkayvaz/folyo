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

    vision_api_key: str = ""
    vision_base_url: str = ""
    vision_model: str = ""

    database_url: str = ""
    chroma_dir: str = "chroma_data"
    storage_dir: str = "storage"

    chunk_chars: int = 1400
    chunk_overlap: int = 210
    temperature: float = 0.2
    data_dir: str = ".ragdata"

    retrieve_dense_k: int = 8
    retrieve_bm25_k: int = 8
    rrf_k: int = 60
    context_chunks: int = 5
    guard_dense_min: float = 0.45
    guard_bm25_min: float = 1.0

    ocr_langs: str = "tur+eng"
    ocr_min_confidence: float = 70.0
    ocr_min_alnum_ratio: float = 0.70
    ocr_min_words: int = 10
    ocr_min_text_coverage: float = 0.05

    image_min_px: int = 100
    image_min_side_px: int = 300
    image_min_area_ratio: float = 0.15

    @property
    def llm_ready(self) -> bool:
        return bool(self.llm_api_key and self.llm_base_url)

    @property
    def embed_ready(self) -> bool:
        return bool((self.embed_api_key or self.llm_api_key) and (self.embed_base_url or self.llm_base_url))

    @property
    def vision_ready(self) -> bool:
        return bool(
            (self.vision_api_key or self.llm_api_key)
            and (self.vision_base_url or self.llm_base_url)
            and self.vision_model
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
