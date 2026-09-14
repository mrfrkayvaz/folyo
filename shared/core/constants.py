"""Ortak sabitler (web-api + worker + panel-api). Servicee-ofis: prompts.py"""

MAX_UPLOAD_SIZE = 25 * 1024 * 1024

DEFAULT_WORKSPACE_NAME = "Yeni sohbet"

ERROR_NO_EMBEDDED_DOCS = (
    "Bu sohbette henüz embedlenmiş belge yok. Bir belge yükleyip dizinlemenin bitmesini bekleyin, sonra sorunuzu sorun."
)

# Aktif embed sürerken soru sorulursa chroma okuma/yazma yarışı 'Error finding id'
# üretir (multi-process) ve akış boş döner. Kullanıcıyı bekletmekz kibarca bilgilendir.
ERROR_EMBED_IN_PROGRESS = "Belgeler hâlâ dizinleniyor; tamamlanınca tekrar sorun."

ERROR_NO_SIMILAR_CONTEXT = "Yüklenen belgelerde sorunuzla yeterli benzerlikte bilgi bulunamadı."

# Chroma sorgusu (retry + exact fallback tükendikten sonra) başarısız olduğunda
# hard-error akışı kesmesin: soft-reject mesajı. Retry/fallback chroma_store içinde
# korunur; bu yalnızca NİHAİ başarısızlıkta kullanıcıya anlamlı geri dönüş verir.
ERROR_RETRIEVAL_FAILED = (
    "Arama altyapısı şu anda yanıt veremiyor (başka bir dizinleme işlemi çakışmış olabilir). "
    "Kısa süre sonra tekrar deneyin."
)

ERROR_QA_GENERIC_FAILURE = "Yanıt alınırken bir hata oluştu."

# panel-api chunks.py (Chroma okuma) kullanır
COLLECTION_NAME = "documents"
