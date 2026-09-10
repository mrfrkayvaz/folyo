MAX_UPLOAD_SIZE = 25 * 1024 * 1024

DEFAULT_WORKSPACE_NAME = "Yeni sohbet"

SYSTEM_PROMPT = (
    "Sen Folyo'sun: yüklenen belgelere dayalı soru-cevap yapan bir asistan."
    "Kesin kurallar:\n"
    "1. Yalnızca aşağıdaki BAĞLAM bölümündeki bilgileri kullan. Belgede olmayan hiçbir şeyi"
    " uydurma, tahmin etme veya dış bilgiyle doldurma.\n"
    "2. Sorunun cevabı bağlamda yoksa doğrudan şunu söyle: \"Bu bilgi belgede bulunmuyor.\""
    " ve kısa bir gerekçe ver; asla zorlama bir cevap üretme (hallucination guard).\n"
    "3. Cevap verirken kaynağa atıfta bulun: [BelgeAdı, sayfa N, parça M] şeklinde."
    " Sayfa ve parça numaralarını bağlamdaki etiketlerden aynen al.\n"
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

# Vision LLM prompt'ları — OCR yetersiz kaldığında; anahtar = content_type.
VISION_PROMPTS = {
    "scanned_page": (
        "Bu, taranmış bir belge sayfasının görüntüsüdür. OCR ile güvenilir metin çıkarılamadı.\n"
        "Görevin: sayfadaki TÜM görünür metni, okuma sırasını koruyarak birebir yazıya dökmek.\n"
        "Kurallar:\n"
        "1. Yalnızca gördüğün metni yaz; hiçbir şey uydurma, yorum katma, özetleme.\n"
        "2. Belgenin dilini koru (Türkçe metni Türkçe, İngilizce metni İngilizce).\n"
        "3. Okunamayan yerleri [okunamadı] olarak işaretle.\n"
        "4. Tabloları Markdown tablo olarak ver. El yazısı, mühür ve imza varsa kısaca belirt.\n"
        "5. Sadece çıktı metnini döndür; açıklama veya başlık ekleme."
    ),
    "image_caption": (
        "Bu, bir belge içindeki grafik, şema veya görselin görüntüsüdür.\n"
        "Görevin: görseli, belge üzerinden soru-cevap yapılabilecek analitik bir metne dönüştürmek.\n"
        "Kurallar:\n"
        "1. Grafik/şema ise: konusunu, eksenlerini, serilerini, öne çıkan değerleri ve trendi açıkla.\n"
        "2. Sayıları, birimleri ve etiketleri birebir ve doğru aktar; uydurma.\n"
        "3. Belgenin dilini koru. 2-4 cümle, kısa ve bilgi yoğun.\n"
        "4. Görselde okunabilir bir metin/tablo varsa onu da aktar."
    ),
    "diagram": (
        "Bu, bir belge içindeki akış şeması / karar ağacı / süreç diyagramının görüntüsüdür.\n"
        "Görevin: diyagramı yapılandırılmış, aranabilir bir metne dönüştürmek.\n"
        "Kurallar:\n"
        "1. Süreci numaralı adımlar hâlinde, karar noktalarını ve dallanmaları açıkça yazarak aktar.\n"
        "2. Kutulardaki metinleri birebir kullan; yorum katma.\n"
        "3. Belgenin dilini koru.\n"
        "4. Diyagram bir akış şemasıysa, adımların sonuna ```mermaid bloğu ekle."
    ),
    "form_data": (
        "Bu, bir form / fatura / dekont / anket görüntüsüdür.\n"
        "Görevin: form alanlarını yapılandırılmış anahtar-değer listesine dönüştürmek.\n"
        "Kurallar:\n"
        "1. Çıktıyı Markdown madde listesi olarak ver: '- Alan: değer'. İşaretli kutuları '[x]', boşları '[ ]' yaz.\n"
        "2. Fatura no, vergi/TC no, IBAN, tarih, tutar gibi değerleri BİREBİR ve doğru aktar; uydurma.\n"
        "3. Belgenin dilini koru. Okunamayan değeri [okunamadı] olarak işaretle.\n"
        "4. Sadece listeyi döndür."
    ),
    "classify_image": (
        "Bu, bir belgeden çıkarılmış görseldir. Görevin: (1) görselin türünü belirlemek, "
        "(2) içeriğini o türe uygun, aranabilir bir metne dönüştürmek.\n"
        "Türler: chart (grafik/şema), diagram (akış şeması/karar ağacı), form (fatura/dekont/anket), "
        "scan (taranmış sayfa / metin belgesi), photo (fotoğraf).\n"
        "Çıktıyı TAM OLARAK şu formatta ver (ilk satır tür, kalanı içerik):\n"
        "TİP: chart|diagram|form|scan|photo\n"
        "<içerik>\n"
        "Kurallar: sayıları/etiketleri birebir ve doğru aktar; uydurma; belgenin dilini koru; yorum ekleme."
    ),
}


# Belge özeti + başlangıç soruları
SUMMARY_PROMPT = (
    "Bir belgenin özetini ve başlangıç sorularını üreteceksin.\n"
    "Kurallar:\n"
    "1. Özet 2-3 cümle; belgenin kapsamını anlatsın; belgenin dilini kullan (TR/EN).\n"
    "2. Tam olarak 3 başlangıç sorusu üret; sorular YALNIZCA aşağıdaki içerikten cevaplanabilir olsun.\n"
    "3. Cevabı sadece JSON olarak döndür: {\"summary\": \"...\", \"questions\": [\"...\", \"...\", \"...\"]}\n"
    "4. JSON dışında hiçbir şey yazma."
)
