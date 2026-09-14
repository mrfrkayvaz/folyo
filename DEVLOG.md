## Problem

Problemde pdf, md, txt, png, jpg, jpeg gibi formatları işleyen ve bu belgeler üzerinden sorulan soruları yanıtlayabilen bir RAG sistemi geliştirmem isteniyor. 

Öncelikle problemi direkt iki parçaya ayırdım:

- Embed: belgelerin yüklenmesi, parçalanması metadataların çıkarılması ve chroma database içinde saklanması
- Retrieve: sorulan soruyla ilişkili olarak veritabanından en alakalı metin parçalarının bulunması ve soruyla birleştirilerek llm'e gönderilmesi

## Tech Stack

projede arayüz için web ve web-api olmak üzere iki servis ayağa kaldırdım. web klasöründe bir react projesi, web-api içinde de fastapi projesi çalışıyor.

web servisinde react, vite, tailwind css, zustand ve typescript kullandım.

web-api servisinde api framework olarak fastapi, paket ve environment yöneticisi olarak uv, vektör database'i olarak chromadb, veritabanı işlemleri yönetimi için asyncpg, async görev yönetimi için de ARQ kullandım.

projede asıl çekirdek kısım panel ve panel-api tarafı. bu iki servis arayüzde dönen işlemleri görmek ve takip etmek için var. ayrıca veritabanı migration'ları yapan asıl kısım da burası. migration işlemleri için alembic kullandım.

ayrıca vektör veritabanı için chroma database, ilişkisel veritabanı için postgresql, kuyruk yönetimi için redis ve kuyrukları işleyen sistem olarak da bir worker ayağa kaldırdım.

tüm servisleri listelersek:

- web
- web-api
- panel
- panel-api
- worker
- chroma
- postgresql
- redis



Yazdırdığım kodlar üzerinde daha fazla hakimiyet kurabilmek ve esneklik sahibi olabilmek için RAG sistemi için LangChain gibi hazır bir kütüphane kullanmadım. Tüm pipeline'i kendim tasarladım.

## Arayüz

sisteme giriş için bir admin user oluşturdum ve sisteme sadece bu admin user bilgileriyle girişi sağladım. belgelerin birbirine karışmaması için workspace mantığı kurguladım. yeni bir sohbet açarak belgeleri yükleyip o şekilde soru sorulabiliyor.

## Upload Sistemi

Arayüzde ilgili dosya yükleme kısmına dosya yüklendiğinde dosyalar **POST /api/workspaces/{wid}/documents** endpointine giderek öncelikle storage içine kaydediliyorlar. storage içine kaydedilmiş dosya için bir embedding işlemi tetikleniyor. bunun için redis üzerinde çalışan ARQ kuyruğuna embed_document görevi bırakılıyor. bu noktadan sonra web-api üzerine düşeni yapmış oluyor. görevi ayrı bir süreç olan worker tüketiyor. worker dosyayı extract etmeye başlıyor.

bir de ön-doğrulama var: desteklenen uzantılar tek bir allowlist'te tanımlı ve hem upload tarafında hem extract yönlendirmesinde aynı liste kullanılıyor. stream okunmadan önce uzantı kontrol ediliyor. desteklenmeyen dosya 415, 25MB'ın üzeri 413 ile reddediliyor. extract tarafında uzantı ile eşleşen handler devreye giriyor. böylece çöp dosyalar storage'a bile girmeden eleniyor ve kullanıcı hızlı hata alıyor.

## Extraction

Bu kısımda gelen dosyanın türüne göre ayrı işlemler gerçekleşiyor.

- pdf
- txt
- md
- png, jpeg, jpg, webp

### PDF Extraction

pdf tüm eklentiler arasında en karışık pipeline'a sahip olanı. çünkü pdf'lerde çok çeşit veri olabiliyor. seçim yapılabilir metinler, seçim yapılamayan metinler, taranmış görseller, resimler, tablolar, denklemler... bunun için iyi bir metin parçalayıcıya ihtiyacım olduğundan PyMuPDF kullandım. genel olarak hızlı çalışan ve pdf içindeki yapıları düzgün çıkarabilen bir eklenti.

PyMuPDF'e geçmeden önce ilk sürümde pypdf kullanmıştım. Ama pypdf sadece extract_text() ile düz metin veriyor. bbox, sayfa ve font bilgisi olmadığı için başlık tespiti, sütun sıralaması, tablo/denklem ayrımı ve header/footer budaması yapamıyordum. Sayfalar tek bir metin bloğuna birleştiği için kaynaklarda sayfa numarasını göstermek mümkün olmuyordu, taranmış bir sayfayı görüntüye çevirip OCR veya vision llm'e verme imkanı da yoktu. 2 sütunlu PDF'lerde okuma sırası karışıyordu ve tablo çıkarımı hiç yoktu. Bu yüzden pypdf'i bırakıp PyMuPDF'e geçtim. pdfplumber'ı da değerlendirdim ama yavaş ve ağır bir bağımlılık olduğu için, PyMuPDF'in find_tables()'ı ihtiyacımı karşıladığından vazgeçtim. Docling/Marker gibi ML tabanlı araçlara da baktım. ama bunlar da çok hantal araçlar yapay zeka tabanlı oldukları için. bu projede asıl önemli olan metin çıkarımından ziyade embeding ve retrieval olduğundan makul bir seçenek olan PyMuPDF'te karar kıldım.

PyMuPDF'ten sadece metni almak yerine sayfayı blok blok tarayıp her bloğun tipini belirliyorum. sayfa düzenine göre doğru sıraya koyuyorum. karşılaştığım türleri şöyle ele alıyorum:

**tablolar:** find_tables metodu ile yakalayıp Markdown tablosuna çeviriyorum. Tablonun hemen üstündeki kısa metni caption alıp chunk'ın başına [Tablo: etiket] satırı ekliyorum ki tablo başlığından kopmasın. 4000 karakteri geçen tabloları satır bazlı bölüyorum ama her parçada tablonun etiketi ve başlığı tekrarlanıyor çünkü chunklar arasında başlıkları da taşımam gerekiyor.

**denklemler:** blok denklemler matematik fontu, sembol oranı gibi değerlerden tespit ediliyor. Önce *pylatexenc* ile yerel olarak Unicode'dan LaTeX'e dönüştürmeyi deniyorum. başarısız olursa ya da blok Office kökenli U+E000–U+F8FF içeriyorsa bbox'ı kırpıp Vision modeline gönderiyorum. Vision tanımlı değilse ham Unicode korunuyor, belge kırılmıyor. Denklemleri mümkün olduğunca metinle aynı chunk'ta tutuyorum. çünkü denklemle ilgili bilgiler genelde yanındaki chunklar'da oluyor.

**kod blokları:** satırların en az %60'ı monospace fontta ise blok kod kabul ediliyor ve bölünmeden tek parça halinde işlem görüyor. bir fonksiyon kodunu ortadan bölmememek için aldığım bir önlem.

**başlık ve liste ayrımı:** başlıkları gövde font boyutuna göre tespit edip breadcrumb olarak taşıyorum, konu başlığı değiştiğinde chunk'ı da bölüyorum. Madde/liste satırlarını (➨ • - 1. gibi) ise başlık saymıyorum. aksi takdirde kaynak düzeninde gövdeden büyük yazılmış her madde başlık sanılıp her biri ayrı chunk'a düşüyordu.

**header ve footer tekrarlayan veriler:** sayfanın üst ve altındaki %10 bandındaki metinlerin sayfalar arası tekrarını sayıyorum. sayfaların en az %60'ında aynı görünenleri sabit başlık veya altbilgi gibi kabul edip eliyorum. Sabit bir oranla körlemesine kırpmak yerine yalnızca gerçekten tekrar edeni atıyorum, sayfaya özel başlıklar duruyor.

**gömülü görseller:** maliyet kısıtından dolayı her görseli işleme almıyorum. kısa kenarı 100px'den küçük görselleri direkt eliyorum, sadece kenarı 300px ve üzeri ya da sayfa alanının %15'inden fazlasını kaplayanları alıyorum. Tekrar eden logo olmasın diye xref bazında tekilleştiriliyor. Bu görselleri önce ocr ile okumaya çalışıyorum. Eğer çoğunlukla yazıdan oluşmuyorlarsa görsel llm'e göndererek ilgili resimdeki tüm bilgiyi metne dökmesini istiyorum. İşlenen görsellerin kırpımlarını **storage/&lt;doc_id&gt;/crops** altına kaydediyorum ki ileride cevapta gösterebileyim. kırpımlara `GET /api/documents/{did}/crops/{name}` endpoint'inden erişiliyor; belge silinince depoyla birlikte temizleniyor.

### TXT Extraction

aralarında en kolay olanı bu. çünkü txt belgeleri düz yazı içerir. ayrıştırması en kolay olan türdür.

### MD Extraction

md dosyalarını da ayrıştırmak nispeten kolaydır. içine tablo yapıları denklem yapıları alabilir. Sistemin bunlara duyarlı olması gerekir. md zaten markdown olduğu için içindeki tablo/denklem yapıları metin olarak korunuyor, ayrı bir dönüşüme gerek kalmadan chunk'lama aşamasına geçiyor.

### png, jpg, jpeg, webp Extraction

resimler için şöyle bir pipeline izleniyor:

pytesseract OCR eklentisiyle resim içerisinde yoğun olarak yazı varsa yazıyı okumaya çalışır. yazı oranı düşükse bu noktada bu resmin yazı içermeyen düz resim olduğuna karar verip görsel llm'e gönderip bu resmi yorumlatmasını ister. görsel llm'den gelen metin yanıtını da kullanmak için kaydeder.



## Chunking

Extraction'dan elde ettiğim segmentleri chunking için belirlediğim stratejilere göre atomik metin bloklarına dönüştürüyorum. burada izlediğim kurallar şunlar:

her segment sayfa bilgisini taşıyor. bu sayede chunk'lar hangi sayfaya ait onu da kaydediyorum. kaynak gösterirken belge, sayfa, parça şeklinde belirtebiliyorum.

chunk boyutu yaklaşık 1400 karakter ve 210 karakter overlap içerecek şekilde belirlendi. overlap'ın amacı bir bilginin sınırda ikiye bölünüp her iki parçada da yarım kalmasını önlemek. kesme noktasını satır veya boşluk sınırına denk getirmeye çalışıyorum. en sondaki çok kısa kuyruk parçasını da önceki chunk'a ekliyorum.

denklemler paragraf bağlamından kopmasın diye text ve equation türleri aynı grupta birleşebiliyor. tablo, kod ve görsel parçaları ise atomik bir şekilde kaydediliyor. 4000 karakteri geçen tabloları satır bazlı bölüyorum ama her parçada tablonun başlığı etiketi tekrarlanıyor ki parçalar bağlamdan kopmasın.

her chunk'a başlık hiyerarşisini chunk içinde metadata olarak ekliyorum. Burada aslında en başta direkt chunk içine ekletiyordum. Denemelerimde çok düşük dense skorları almaya başlayınca sorunun bundan kaynaklandığını anladım. Çünkü chunk'lardaki bilgiler bu başlıkların yanında küçük kalınca chunk'lar çok benzeşmeye ve birbirinden ayrılamamaya başlıyordu. Bunu geri alıp metadata şeklinde ekledim.

her chunk taşıdığı metadata: sayfa numarası, content_type, page_context, breadcrumbs, section_title, bbox, image_path. burdaki bbox o chunkin barındığı yerin sayfadaki koordinatı.

## Vektör Database

chunk'lar hazır olunca embedding aşamasına geçiyorum. şu anda BAAI/bge-m3 modelini kullanıyorum. bu modele geçmeden önce text-embedding-3-small kullanıyordum. ancak türkçe kısa sorgularda ilgili ve ilgisiz parçaları ayırt edemiyordu. bge-m3 ile ayrışma belirgin şekilde iyileşti. bunu ölçümle de gösterdim: ilgili parçada kosinüs 0.686, aynı belgenin başka bir parçasında 0.274, alakasız parçada 0.248. eskisinde böyle bir ayrım yoktu. geçişte chroma, storage ve db'yi sıfırlayıp temiz sayfadan başladım. bu önemli çünkü aksi halde farklı embedder'lar tarafından kodlanmış veriler sistemin yanlış çalışmasına neden olacaktı.

tüm vektörleri hafızada biriktirmiyorum. 64'lük batch'ler halinde modelden çekip her batch biter bitmez chroma'ya yazıyorum. RAM'in çok şişmemesi için önemli bir durum yine RAG sistemlerinde.

batch'ler paralel çekiliyor ama embedding işlemini hızlı olmasını sağlamak için embed_max_concurrency=4 şeklinde eş zamanlayıcı veriyorum. chunklar aynı anda 4 kanaldan işlenmeye başlıyor. 

yazma işlemi upsert ile aynı chunk id'si üzerine tekrar yazılabiliyor. bunu bilinçli yaptım çünkü arq içindeki retry mekanizması yarıda kalan bir işi yeniden koştuğunda çakışma olmamalı. bu da işlemin idempotent olmasını sağlıyor.

tüm yazım bitince o workspace'in bm25 indeksini geçersiz kılıyorum. böylece sonraki arama yeni belgeyi görüyor. workspace içindeki belgelerde değişiklik olduğunda bu indeksi yenilemem gerekiyor. aksi halde yeni gelen belgede bm25 araması yapılmaz.

## Belge Özeti ve Önerilen Sorular

bu kısım opsiyonel ama ürünün daha iyi gözükmesi için böyle bir kısım ekledim. kullandığım llm ve openrouter yönlendiricisi biraz gecikme yaptığı için bu kısımda biraz yavaşlık hissediliyor. yine de bu kısmı beklemeden kullanıcı sorusunu sorabiliyor.

toplamda yaklaşık 2500 karakter sınırı olacak şekilde chunklar'dan temsili yerleri, başlıkları, belge başını, ortasını, sonunu alıp llm'e gönderip özet ve soru çıkarımı yapmasını istiyorum.

tek çağrıda {summary, question} şeklinde json çıktı istiyorum. burada dönen json verisi llm kaynaklı olarak bazen bozuk geliyordu. bunun için veriden alabildiği kısmı alabilecek bir onarım kodu yazdırdım.

soru sayısına eşik koymuyorum. 1-6 arası olacak şekilde  model kendisi karar veriyor. yani belge önemli ve yoğun bilgi içeriyorsa 6, ama hiç bilgi içermiyorsa 1 olacak şekilde soru hazırlıyor.

workspace de içindeki belgelerden özetleri toplayıp kendine özet çıkartıyor. dokümanların sorularından da rastgele gösterim yapıyoruz arayüzde.

## Soru Sorma

Deneme yanılmayı en çok bu kısımda yaptım. Bu kısımda bir de ne dönüp bittiğine daha iyi hakim olmak gerekiyor. bunun için de loglama sistemi en çok burada işe yaradı. şuanki bilgimle en başa dönsem burada bahsettiğim loglama sistemini en baştan düzgün bir şekilde kurardım. geliştirme hızımı kesinlikle arttırırdı.

En başta sağlam bir temel oluşturabilmek için basit RAG sistemlerinde olan yapıyı kurdum. Normal dense search. vektör veritabanına kaydettiğimiz veriler arasında anlamsal arama yapıyor ve ona göre en yakın olabilecek maksimum 8 chunk'ı döndürüyor. bu sistemi kurup çalıştırabildim başarılı bir şekilde.

dense search anlamsal yakınlığı bulmada iyi ama nokta atışı metinleri hesaplamada yine eksik kaldığı için bm25 search de ekledim sisteme. buradan da yine 8 tane en yüksek skorlu chunklar geliyor.

burada yaşadığım bir sorun türkçe karakter problemleriydi. bm25 için custom bir tokenizer yazmam gerekti. ç, ş, ğ, ü, ö, İ-&gt;i, I-&gt;ı gibi dönüşümler ve özel karakterlere ek olarak kök eşleşmelerini de sağladım. çevirmeli -&gt; çevirmelisiniz gibi çekim farkları yakalanıyor. ilk tokenizer ASCII tabanlıydı ve çıktığında kelimesini kt+nda diye parçalıyordu. canlı sorguyla görüp düzelttim. kahveli tarif sorgusunda cevap parçasının bm25 skoru 0.83'ten 5.96'ya çıktı ve güven oranı 66'dan 94'e yükseldi.



burada çektiğim chunk'ların her biri için aşağıdaki doğrulamayı yapıyorum ve ona göre elemeden geçen chunkları alıyorum. iki sorgudan birinden geçmesi gerekiyor. bu eşik değerlerini de kendim ayarlayarak belirledim.

eğer skor geçerin altındaysa llm'e hiç gitmeden ön yüzde "yüklenen belgelerde sorunuzla yeterli benzerlikte bilgi bulunamadı" metnini gösteriyorum. böylece belgeyle ilgisiz sorularda maliyet ve halüsinasyon riski sıfırlanıyor. bu eşikler ilk başta 0.72/4.0 idi ama türkçe kısa sorgularda gerçekçi kosinüs 0.24-0.42 bandında kaldığı için her şeyi reddediyordu. yani türkçe kısa soruları kaybetmemek için eşiği biraz daha aşağı çektim. ingilizce sorularda skor bu kadar düşmüyor. çünkü metin daha iyi eşleştirme yapabiliyor ingilizcede. 

$$
\text{geçer} \iff \max(d_i) \ge 0.30 \;\lor\; \max(b_j) \ge 1.0
$$

($d_i$: dense skorları, $b_j$: bm25 skorları)



iki kanaldan gelen parçaları rank tabanlı birleştiriyorum. her parça ulaştığı kuyruk pozisyonundan `1/(k+rank+1)` puan alıyor, iki kanalda birden geçen parça iki puan topluyor. mantığım şu: tek kanalın yüksek puanından ziyade iki kanalın aynı parçada buluşması daha güçlü sinyal. buradan seçilen en iyi skorlu 5 chunk soru ile birleştirilerek özel bir prompt formatında llm'e gidiyor.

$$
\mathrm{RRF}(p) = \frac{1}{k + r_{dense}(p) + 1} + \frac{1}{k + r_{bm25}(p) + 1}, \qquad k = 15
$$



Altta beni en çok oyalayan hataları, durumları ve aldığım irili ufaklı karar senaryolarına yer verdim.

### 09.09.26 pdf önizlemede vurgulama denemesi

pdf önizlemesinde kaynağın geçtiği yeri vurgulamayı denedim ama tam istediğim gibi olmadı. çünkü chrome kendi pdf önizleme aracında çizim işini biraz zorlaştırıyor. on-the-fly şekilde pdf render front end kısmını biraz yoruyor. şimdilik bu fikri bıraktım.

### 09.09.26 top_k ile yanlış parça sayısı, threshold geldi

sistem ilgisiz sorularda bile en alakalı 6 parçayı döndürüyordu ve ön yüz "yararlanılan parça" olarak 6 gösteriyordu. bu hem gereksiz maliyetti hem yanlış gösterimdi. bir threshold ekledim; eşiğin altında kalan parçalar değerlendirmeye girmiyor. böylece hem llm'e giden veri azaldı hem ön yüzdeki parça sayısı doğru olmaya başladı.

### 10.09.26 birebir eşleşme: regex mi bm25 mi?

spesifik bilgilerde (fatura no, tc no, telefon) semantik yakınlık yetmiyor. birebir eşleşme gerekiyor. bu noktada iki seçenek vardı: regex ya da bm25. regex ancak belge türlerini bilirsek işe yarar. sistemimize her tür belge girebildiği için sadece bm25 kullandım ve custom bir tokenizer yazdım: sayılar arasındaki - işaretleri de dahil. daha spesifik RAG sistemleri için farklı custom tokenizer'lar yazılabilir.

### 10.09.26 HyDE ve re-ranker'a baktım, ikisini de almadım

HyDE sistmei yani soruyu llm'de genişletip o şekilde embed'leme mimarisini sistemime dahil etmedim. soyut sorularda eşleşmeyi artırabilir ama gecikme ve maliyet getiriyor.

aynı sebeple re-ranker mimarisini de eledim. bu mimari chunklar'ı basit bir cross-encoder llm'e gönderip ona sıralatma şeklinde. ek bir model, ek maliyet ve gecikmeye sebep olduğu için bu kısmı eledim. ikisinin yerine dense ve bm25 skorlarını birleştirip karma bir skor üretip sıralamayı buradan yapmayı seçtim.

### 10.09.26 mimariyi arch.md üzerinden kararlaştırma

mimari kararları koda dökmeden önce arch.md yöntemim var: konuyu adım adım llm ile konuşup son haline getiriyorum, belirsiz kalan yerlerde bana soru sormasını istiyorum, karşılıklı netleştiriyorum. dosya netleşince geriye sadece onu koda dökmek kalıyor.

### 10.09.26 cosine yerine l2 metriğini kullanıyordum

bir süre dense skorlar hep düşük ya da negatif geliyordu, eşik asla geçilmiyordu. her şeyi bm25 taşıyordu. uzun süre eşiklerle uğraştım. sonra koleksiyonun eski kurulumdan kalma l2 uzayıyla oluşturulduğunu fark ettim. chroma bana distance veriyordu. ben de skoru 1 - distance diye hesaplıyordum. l2 skoru karesel uzaklık olduğu için bu negatif çöp üretiyordu. cosine olarak düzeltip yeniden belgeleri embed'ledim ve skorlar gerçek kosinüslere (+0.31…+0.34) oturdu.

### 11.09.26 qa boş yanıt veriyordu

belge yüklenip embedlendikten sonra sorulara boş dönüyordu. nedenini uzunca bir süre araştırdım. en son buldum. chroma sqlite dosya tabanlı. web-api ve worker iki ayrı süreç ama aynı dosyaya erişiyor. çözüm için chroma'yı http/single-writer moda aldım.

### 13.09.26 create_task'tan ARQ'ya geçiş

başta embed işlerini web-api sürecinde `asyncio.create_task` ile koşturuyordum. ancak hatalar izlenemiyordu. restart in-flight işi kesiyordu. yeniden deneme katmanı yoktu. bu yüzden iş yürütmeyi süreç olarak ayırdım ve ayrı bir servis açtım. redis üzerinde arq kuyruğu ve ayrı bir worker süreci oluşturdum. web-api bu sistemde sadece kuyruğa iş atma görevini yapıyor ve gerisine karışmıyor. bu da servisler arası izolasyonu sağlıyor.

### 13.09.26 shared sistemi

en başta bir panel bile kurmak istemedim. ancak sonrasında yönetim için gerektiğini fark ettim. sonrasında kodların çok izole ve atomik olmasını istediğim için worker işlemlerini ayrı bir servise taşıdım. bu güzel bir avantajdı. ancak bir dezavantaj getirdi. kopya dosyalar oluştu. çözüm için shared servisi oluşturup ortak dosyaları buraya aldım.

### 14.09.26 text llm promptu yetersizdi

halüsinasyon görmemesi için prompta katı bir şekilde belgeye sadık kalması gerektiğini eklemiştim. bu sefer de belgenin iki farklı yerinden bir araya getirip yorumlayabileceği şeyleri yorumlamıyor ve belgede bunlar yok diyordu. [TESTING.md](http://TESTING.md) içerisinde bunun örneği var. çok ama çok kritik bir o kadar da basit bir eklemeyle prompt içerisinde yorum yeteneği de bıraktım. tabi ki yorumladığı şeyler yine belgeden elde ettiği şeylerden ibaret. mantıksal çıkarımlar yapmasının önünü açmış oldum sadece.



### Zamanlama

1 gün -&gt; ui

1 gün -&gt; backend altyapısı

2 gün -&gt; basit rag altyapısı, chroma data

1 gün -&gt; promptlar, vision llm eklentisi, optimizasyonlar

1 gün -&gt; test senaryoları