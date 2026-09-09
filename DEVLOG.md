### 07.09.2026

### 08.09.2026

### 09.09.2026

pdflerin birbirine karışmaması için workspace mantığı kurguladım.

yüklenen belgeler ilgili workspacelere workspace_id üzerinden bağlanıyor.

belge yüklendiğinde önce documents tablosuna belge kaydını yapıyor ve yüklendiği anda embedding işlemine gönderiliyor. süreç ön yüzden böylelikle takip edilebiliyor. belgeler yüklenene kadar soru sormaya izin verilmiyor. belgeler yüklendiğinde de input artık aktif hale geliyor.

pdf önizlemesinde ilgili yeri vurgulamayı denedim ama tam olarak ilgili yeri vurgulamayı başaramadım. farklı bir strateji deneyeceğim.

prompt sayesinde halusinasyon görmüyor.
örneğin;
türkiye'nin başkenti neresidir? diye sorduğumda bu belgede ilgili ifadenin olmadığını belirtti.

hem api tarafının hem de fronend tarafının kodlarını ai yardımıyla düzenledim. constants, types, enums gibi yapıları ortak kullanım sağlayabilmek için kendi dosyaları içerisine çektim.

uzun dosyaların oluşmaması ve tekrarlı kullanımı sağlayabilmek için iki tarafta da component yapısı uyguladım. tekrar kullanabileceğim her yeri component haline getirdim.

rag sisteminden top_k=6 şeklinde ifade dönüyordu. burada belgeyle ilgili olmayan bir şey sorduğumda belgeyle ilgisinin olmadığını tespit edebilmesine rağmen en alakalı 6 chunkı döndürdüğü için ön yüzde yararlanılan parça sayısına 6 yazıyordu. bu nedenle threshold ekledim. yani gelen chunklar bu thresholdun altında kalıyorsa değerlendirmeye dahil edilmiyor artık. bu hem llm'e gönderilen veri miktarını azalttığı için maliyet optimizasyonu ve hız sağlıyor hem de ön yüzde yararlanılan parça sayısını yanlış göstermemiş oluyor.

### 10.09.2026

### 11.09.2026

### 12.09.2026

### 13.09.2026

### 14.09.2026
