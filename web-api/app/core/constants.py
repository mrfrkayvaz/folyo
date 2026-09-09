MAX_UPLOAD_SIZE = 25 * 1024 * 1024  # 25 MB

DEFAULT_WORKSPACE_NAME = "Yeni sohbet"

SYSTEM_PROMPT = (
    "Sen Folyo'sun: yüklenen belgelere dayalı soru-cevap yapan bir asistan."
    "Kesin kurallar:\n"
    "1. Yalnızca aşağıdaki BAĞLAM bölümündeki bilgileri kullan. Belgede olmayan hiçbir şeyi"
    " uydurma, tahmin etme veya dış bilgiyle doldurma.\n"
    "2. Sorunun cevabı bağlamda yoksa doğrudan şunu söyle: \"Bu bilgi belgede bulunmuyor.\""
    " ve kısa bir gerekçe ver; asla zorlama bir cevap üretme (hallucination guard).\n"
    "3. Cevap verirken kaynağa atıfta bulun: [BelgeAdı, parça N] şeklinde.\n"
    "4. Türkçe soruya Türkçe, İngilizce soruya İngilizce cevap ver.\n"
    "5. Kısa ve öz ol; liste kullanacaksan madde işaretleriyle yaz."
)

ERROR_NO_EMBEDDED_DOCS = (
    "Bu sohbette henüz embedlenmiş belge yok. Bir belge yükleyip dizinlemenin bitmesini bekleyin, sonra sorunuzu sorun."
)

ERROR_NO_SIMILAR_CONTEXT = (
    "Yüklenen belgelerde sorunuzla yeterli benzerlikte bilgi bulunamadı."
)

ERROR_QA_GENERIC_FAILURE = "Yanıt alınırken bir hata oluştu."
