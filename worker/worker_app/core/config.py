from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Worker'a özgü yapılandırma — yalnızca embed/enrich/summary akışının okuduğu alanlar.

    (web-api'nin QA/RAG tarafındaki tuning alanları bu kopyada yok — izolasyon.)
    """

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
    # Uzaktan chroma server (bağımsız servis — HTTP). Boşsa hata verilir.
    chroma_host: str = ""
    chroma_port: int = 8000
    storage_dir: str = "storage"

    chunk_chars: int = 1400
    chunk_overlap: int = 210
    temperature: float = 0.2

    # BM25 tokenizer (Türkçe): Unicode kelime + hafif kök (prefix) eşleşmesi.
    bm25_stem_min: int = 4   # sorgu token'inin kök uzunluğu (çevirmeli ↔ çevirmelisiniz)
    bm25_stem_cap: int = 24  # token başına eşleştirilecek en çok ön-ekli terim (maliyet sınırı)

    ocr_langs: str = "tur+eng"
    ocr_min_confidence: float = 70.0
    ocr_min_alnum_ratio: float = 0.75
    ocr_min_words: int = 10
    ocr_min_text_coverage: float = 0.05
    # Diyagram/infografik bekçisi: OCR kabul edilebilir olsa bile yoğunluk altındaysa
    # görsel tipi chunk üretilir (Vision maliyeti olmadan — OCR metni içeriktir).
    ocr_diagram_max_words: int = 25
    ocr_diagram_max_coverage: float = 0.15
    # Sabit başlık/altbilgi bekçisi: sayfaların ≥ bu oranında aynı (metin, y-bandı) → atıl.
    header_footer_repeat_ratio: float = 0.6
    # Tablo tek parça üst limiti; üstündeki tablolar satır bazlı bölünür (embed truncate koruması).
    table_max_chars: int = 4000
    # Blok denklem tespiti (extract/equations.py): satır limiti, sembol oranı, ortalama payı.
    equation_max_lines: int = 5
    equation_min_symbol_ratio: float = 0.25
    equation_center_margin: float = 0.15
    equation_vision_padding: int = 6
    equation_vision_dpi: int = 200
    # LLM/API eşzamanlılık sınırları: çağrılar paralel akar ama sağlayıcı boğulmaz.
    vision_max_concurrency: int = 6    # Vision LLM eşzamanlı istek tavanı
    embed_max_concurrency: int = 4     # Embedding batch eşzamanlı tavanı
    # OCR (Tesseract) CPU işidir — sınırsız paralel thread yarışını engelle.
    ocr_max_concurrency: int = 3
    # Embed akışlı yazma için bilgi eşiği: bu kadar chunk üzerinde warning logluyoruz
    # (vektörler RAM'de toplanmaz — batch batch kuyruğa/Chroma'ya yazılır).
    embed_memory_warning_chunks: int = 2000
    # ARQ görev kuyruğu.
    redis_url: str = "redis://localhost:6379/0"

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