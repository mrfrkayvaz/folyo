"""Uygulama geneli sabitler. (Prompt metinleri: `prompts.py`.)"""

MAX_UPLOAD_SIZE = 25 * 1024 * 1024

DEFAULT_WORKSPACE_NAME = "Yeni sohbet"

ERROR_NO_EMBEDDED_DOCS = (
    "Bu sohbette henüz embedlenmiş belge yok. Bir belge yükleyip dizinlemenin bitmesini bekleyin, sonra sorunuzu sorun."
)

ERROR_NO_SIMILAR_CONTEXT = "Yüklenen belgelerde sorunuzla yeterli benzerlikte bilgi bulunamadı."

ERROR_QA_GENERIC_FAILURE = "Yanıt alınırken bir hata oluştu."
