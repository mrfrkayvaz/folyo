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

    # Web girişi (auth) — HMAC token anahtarı + süre. Prod'da AUTH_SECRET set edilmeli.
    auth_secret: str = ""
    auth_token_ttl_hours: int = 24

    database_url: str = ""
    # Uzaktan chroma server (bağımsız servis — HTTP). Boşsa hata verilir.
    chroma_host: str = ""
    chroma_port: int = 8000
    chroma_ssl: bool = False
    storage_dir: str = "storage"

    chunk_chars: int = 1400
    chunk_overlap: int = 210
    temperature: float = 0.2
    data_dir: str = ".ragdata"

    retrieve_dense_k: int = 8
    retrieve_bm25_k: int = 8
    rrf_k: int = 60
    context_chunks: int = 5
    # Koleksiyon cosine uzayında; ölçülen ilgili-chunk kosinüs dağılımı (BGE-M3, TR kısa sorgu)
    # ~0.30-0.55 bandında. 0.38 çoğu doğru eşleşmeyi eliyordu → 0.30'a kalibre edildi.
    guard_dense_min: float = 0.30
    guard_bm25_min: float = 1.0
    # BM25 tokenizer (Türkçe): Unicode kelime + hafif kök (prefix) eşleşmesi.
    bm25_stem_min: int = 4   # sorgu token'inin kök uzunluğu (çevirmeli ↔ çevirmelisiniz)
    bm25_stem_cap: int = 24  # token başına eşleştirilecek en çok ön-ekli terim (maliyet sınırı)
    # Sürekli güven skoru (formül) — taşıyıcı (carrier) yolu:
    # hangi kanal kanıtı taşıyorsa o yol skoru belirler; her yolun ağırlıkları toplamı = 100.
    #   dense yolu = norm·d + (100 − norm)·c
    #   bm25 yolu  = norm·b + (100 − norm − bonus)·c + bonus·d
    confidence_dense_min: float = 0.15    # BGE-M3 TR gerçekçi alt taban (norm başlangıcı)
    confidence_dense_max: float = 0.70    # doyum — alakalı ölçüm ~0.69
    confidence_bm25_sat: float = 5.0      # ham BM25 doyumu (log-ölçek)
    confidence_path_dense_norm: float = 92.0   # dense yolunda dense ağırlığı (kalan: uzlaşma)
    confidence_path_bm25_norm: float = 64.0    # bm25 yolunda bm25 ağırlığı
    confidence_path_kind_bonus: float = 8.0    # bm25 yolunda dense bonusu (kalan: uzlaşma)
    confidence_dense_blind_floor: float = 74.0  # dense yok + güçlü BM25 → taban (eski 75-80 kararı)
    confidence_min_answered: float = 55.0       # kalkan geçtiyse daima ≥ bu (dolaylı eşiği üstü)

    ocr_langs: str = "tur+eng"
    ocr_min_confidence: float = 70.0
    ocr_min_alnum_ratio: float = 0.75
    ocr_min_words: int = 10
    ocr_min_text_coverage: float = 0.05
    # Dev CORS: virgülle ayrılmış origin listesi (boşsa CORS middleware eklenmez).
    # Prod'da frontend aynı-origin /api kullandığından genelde gerekmez.
    cors_origins: str = (
        "http://localhost:5173,http://localhost:5174,http://localhost:8080,http://localhost:8081"
    )
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
    # ARQ görev kuyruğu (embed/enrich işleri ayrı worker sürecinde çalışır).
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
