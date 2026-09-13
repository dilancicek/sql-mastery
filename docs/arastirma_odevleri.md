# Bölüm 3.6 Araştırma Ödevleri

---

## Araştırma Ödevi 1: OLTP vs OLAP Mimarisi, Satır ve Kolon Bazlı Depolamanın Performans Analizi

### 1. Giriş ve Veri Mimarisine Genel Bakış
Modern veri mimarisinde veritabanı sistemleri temel olarak iki ana iş yükü sınıfına ayrılır: **OLTP (Online Transaction Processing - Çevrimiçi İşlem İşleme)** ve **OLAP (Online Analytical Processing - Çevrimiçi Analitik İşleme)**. Bu iki mimari arasındaki temel fark sadece sorgulama dilinde veya indeksleme yöntemlerinde değil, verinin diske fiziksel olarak nasıl yazıldığı ve diskten belleğe nasıl okunduğu mimari mantığında yatmaktadır. 

Yazılım sistemlerinin ilk günlerinden itibaren geleneksel ilişkisel veritabanları (RDBMS) veriyi **satır tabanlı (row-oriented)** olarak depolarken, modern analitik motorlar veriyi **kolon tabanlı (column-oriented)** veya sıkıştırılmış analitik dosya formatlarında (Parquet, ORC vb.) tutmaktadır. Bu dokümanda, satır ve kolon tabanlı depolama mimarilerinin iç çalışma mekanizmaları incelenecek ve NYC Taxi veri seti üzerinde Pandas (satır odaklı/bellek odaklı) ile DuckDB (kolon tabanlı OLAP) araçlarıyla gerçekleştirdiğimiz deneysel performans testlerinin sonuçları analiz edilecektir.

---

### 2. Fiziksel Depolama Mimarisi ve İç Mekanizmalar

#### 2.1 Satır Bazlı Depolama (Row-Oriented / OLTP)
PostgreSQL, MySQL ve SQLite gibi geleneksel ilişkisel veritabanı sistemleri veriyi diske satır sırasına göre yazar. Bir tablodaki tek bir kayıt (row), diskin bloklarında yan yana bulunan baytlarda saklanır. Örneğin bir kullanıcı tablosunda id, isim, e-posta ve kayıt tarihi bilgileri disk üzerinde ardışık adreslerde tutulur.

*   **Avantajları:**
    *   **Yüksek Ekleme/Güncelleme Hızı:** Yeni bir satır eklendiğinde (`INSERT`), veri doğrudan ilgili sayfanın veya bloğun sonuna tek bir I/O işlemiyle yazılır.
    *   **Tekil Kayıt Erişimi (Point Queries):** İlgili kaydın Primary Key değeri biliniyorsa (örn: `SELECT * FROM users WHERE id = 105`), veritabanı B-Tree indeksi kullanarak o satırın diski kapladığı tek bir adrese gider ve tüm kolonları tek hamlede okur.
*   **Analitik Sorgulardaki Dezavantajı:**
    *   **Gereksiz I/O Maliyeti:** Milyonlarca satırlık bir `orders` tablosunda sadece ortalama tutarı (`AVG(total_amount)`) hesaplamak istediğinizde, veritabanı motoru diski satır satır taramak zorundadır. Satır tabanlı yapıda müşteri adı, adresi, sipariş notu gibi sorguda **kullanılmayan tüm kolonlar da diskten belleğe okunur**. Bu durum devasa bir I/O (Input/Output) darboğazına sebep olur.

#### 2.2 Kolon Bazlı Depolama (Column-Oriented / OLAP)
DuckDB, Snowflake, ClickHouse ve Apache Parquet gibi teknolojiler ise veriyi kolon kolon gruplayarak saklar. Yani tablodaki tüm `total_amount` değerleri disk üzerinde art arda gelen bloklarda depolanırken, `passenger_count` değerleri ayrı bir blok kümesinde depolanır.

*   **Avantajları:**
    *   **Minimum Disk Read (I/O Optimizasyonu ve Projection Pushdown):** Bir sorgu sadece 2 kolona ihtiyaç duyuyorsa (`passenger_count` ve `tip_amount`), veritabanı diskten sadece o iki kolona ait blokları okur. Diğer 15 kolona hiç dokunmaz ve disk okuma yükünü %90'a varan oranlarda azaltır.
    *   **Yüksek Sıkıştırma Oranları:** Aynı kolondaki veriler aynı veri tipindedir (örn: hepsi tam sayı veya hepsi tarih). Benzer veriler dizisi Snappy, ZSTD, Run-Length Encoding (RLE) veya Dictionary Encoding gibi tekniklerle muazzam oranlarda sıkıştırılabilir. Örneğin 3 GB'lık ham CSV verisi Parquet formatında ~50 MB'a kadar büzülebilir.
    *   **Vektörel Sorgu İşleme (Vectorized Execution):** CPU önbelleğine (L1/L2/L3 cache) tek seferde aynı tipteki binlerce sayı çekilerek SIMD (Single Instruction, Multiple Data) talimatlarıyla paralel olarak işlenebilir.

---

### 3. CPU Donanım Mimarisi ve Bellek Hiyerarşisi Etkisi

Satır ve kolon bazlı depolama arasındaki performans farkı sadece disk I/O operasyonları ile sınırlı değildir; modern CPU mimarisi ve RAM erişim hızları düzeyinde de belirleyicidir.

Modern işlemciler veriyi RAM'den işlemek yerine L1, L2 ve L3 önbelleklerine (cache line - genelde 64 baytlık bloklar) yükleyerek çalışır. Satır tabanlı bir yapıda, bir önbellek çizgisine sorguyla ilgisiz diğer kolonların verileri de dolar. Bu durum "Cache Pollution" (Önbellek Kirlenmesi) yaratarak işlemcinin sık sık RAM'e gitmesine (Cache Miss) neden olur.

Kolon tabanlı depolamada ise tek bir önbellek çizgisine sadece işlenecek kolonun verileri dizilir. İşlemci önbellek isabet oranını (Cache Hit Rate) maksimuma çıkarır ve komut düzeyinde paralellik sağlayarak döngüleri (loops) donanım seviyesinde hızlandırır.

---

### 4. Deneysel Performans ve Bellek (RAM) Test Sonuçları

Teorik farkları pratikte kanıtlamak amacıyla NYC Taxi (Ocak 2024 Parquet formatındaki yaklaşık 3 milyon satırlık veri kümesi) üzerinde kapsamlı bir kapışma testi gerçekleştirilmiştir.

Test ortamında bellek yönetimi `tracemalloc` ile anlık izlenmiş, adil bir test için her tur öncesinde Python çöp toplayıcısı (`gc.collect()`) çalıştırılmıştır. 10 farklı karmaşık analitik iş sorgusu (agregasyon, tarih filtreleme, oran hesaplama vb.) her iki motorla da koşturulmuştur.

#### 4.1 Deneysel Ölçüm Tablosu

| Metrik | DuckDB (OLAP / Disk Üstü Kolonsal) | Pandas (Bellek Tabanlı / Satır Esaslı) | Fark / Çarpan |
| :--- | :--- | :--- | :--- |
| **Toplam Çalışma Süresi** | **0.3731 saniye** | **6.9533 saniye** | **DuckDB 18.6x Daha Hızlı** |
| **Pik RAM Tüketimi** | **0.01 MB** | **762.53 MB** | **Pandas 58.645x Daha Fazla RAM** |
| **Veri Okuma Stratejisi** | Doğrudan Diskten Sadece İlgili Kolonlar | Dosyanın Tamamını RAM'e Unpack Etme | Devasa I/O İzi |

#### 4.2 Ölçüm Sonuçlarının Mühendislik Değerlendirmesi

1.  **Bellek Taşması (Out of Memory) Riski:** Pandas, yapısı gereği 50 MB'lık sıkıştırılmış Parquet dosyasını diskten okuyup kendi Dataframe yapısına açtığında veri aniden şişerek **762.53 MB RAM** harcamıştır. Eğer veri setimiz 3 GB boyuta ulaşsaydı, Pandas bellek sınırını aşarak sistemi kilitlerdi. DuckDB ise sorguları disk üzerinden yürüttüğü için pik bellek kullanımını **0.01 MB** gibi sembolik bir seviyede tutmuştur.
2.  **Hızlanma Katsayısı:** DuckDB'nin 10 analitik sorgunun tamamını **0.3731 saniyede** (Pandas'ın 6.9533 saniyesine kıyasla) tamamlaması, vektörel sorgu motorunun ve kolon seçiminin (projection pushdown) gücünü göstermektedir.

---

### 5. Sonuç ve Mimari Karar Çerçevesi

Bir veri mimarı veya veri mühendisi olarak sistem tasarlarken doğru depolama motorunu seçmek hayati önem taşır:

*   **Ne Zaman OLTP (PostgreSQL) Seçilmeli?:** Sistem kullanıcı etkileşimli, sık transactional (ACID kısıtlı) yazma işlemleri yapıyorsa, kullanıcı profili güncelleniyor, anlık sipariş veya ödeme oluşturuluyorsa tercih edilmelidir.
*   **Ne Zaman OLAP (DuckDB / Parquet) Seçilmeli?:** Büyük veri setleri üzerinde raporlama, dashboard besleme, ML özellik mühendisliği (Feature Engineering) veya ad-hoc analitik sorgular koşturulacaksa tercih edilmelidir.

Sonuç olarak; analitik veri işleme süreçlerinde OLTP mantığıyla çalışan kütüphaneler yerine kolon tabanlı ve sunucusuz (serverless) çalışabilen DuckDB gibi OLAP teknolojilerini kullanmak, donanım maliyetini düşürürken veri işleme hızını katbekat artırmaktadır.

---

---

## Araştırma Ödevi 2: SCD Type 2 Nedir ve Neden ML Özelliği Üretirken Kritiktir?

### 1. Giriş: Boyut Değişimi ve Veri Mimarisi Problemi
İlişkisel veritabanları ve veri ambarlarında müşteri adresi, üyelik segmenti, ürün fiyatı veya kredi skoru gibi boyut (dimension) verileri zaman içinde değişir. Yavaş Değişen Boyutlar (Slowly Changing Dimensions - SCD), boyut verilerindeki bu değişikliklerin veritabanında nasıl yönetileceğini belirleyen tasarım desenleridir.

Makine öğrenmesi (ML) ve yapay zeka sistemlerinde, modellerin geçmiş veriler üzerinden eğitilmesi esastır. Geçmiş tarihli veri setlerinden özellik (feature) türetirken verinin zaman içerisindeki durumunu doğru yansıtamamak, ML projelerinin başarısız olmasındaki bir numaralı teknik sebep olan **Veri Sızıntısı (Data Leakage / Target Leakage)** problemine yol açar. Bu çalışmada SCD Type 2 mimarisi ve bu yapının ML özellik mühendisliğindeki kritik rolü incelenecektir.

---

### 2. SCD Tipleri ve SCD Type 2 Mekanizması

Veri ambarı literatüründe yaygın olarak kullanılan temel SCD yaklaşımları şunlardır:

*   **SCD Type 1 (Overwriting / Üzerine Yazma):** Değişen verinin eski halini tamamen siler ve yeni veriyi üzerine yazar. Geçmiş tarihçe tutulmaz. (Örn: Müşteri adresi değiştiğinde eski adres sistemden silinir).
*   **SCD Type 2 (History Tracking / Tarihçe Tutma):** Eski veriyi asla silmez veya ezmez. Her değişiklikte tabloya **yeni bir satır** eklenir. Zaman boyutunu yönetebilmek için satıra `valid_from` (geçerlilik başlangıcı), `valid_to` (geçerlilik bitişi) ve `is_current` (güncel kaydolup olmadığı) kolonları eklenir.
*   **SCD Type 3 (Previous Value Column / Önceki Değer Kolonu):** Sadece bir önceki değeri tutmak için tabloya `previous_segment` gibi ekstra bir kolon ekler. Sınırlı bir tarihçe sunar.

#### SCD Type 2 Veri Yapısı Örneği
Bir müşterinin segment değişikliği SCD Type 2 tablosunda şu şekilde tutulur:

| customer_id | segment | valid_from | valid_to | is_current |
| :--- | :--- | :--- | :--- | :--- |
| 101 | Standard | 2023-01-01 | 2024-05-31 | False |
| 101 | VIP | 2024-06-01 | 9999-12-31 | True |

---

### 3. Veri Sızıntısı (Data Leakage / Lookahead Bias) Nedir?
Makine öğrenmesi modellerinde "Data Leakage", modelin eğitim esnasında erişememesi gereken (geleceğe ait olan veya hedef değişkenin bilgisini içeren) verileri kullanması durumudur.

Geleceği görme yanlılığı (Lookahead Bias / Time-Travel Leakage), geçmiş bir olayı tahmin ederken, o olayın gerçekleştiği tarihten **sonraki** bir durumu modelin girdisi olarak sunmaktır. Bu tür sızıntılar eğitim aşamasında yapay olarak mükemmel performans skorları (örn: %99 accuracy) verirken, model üretime alındığında tam bir fiyaskoyla sonuçlanır.

---

### 4. SCD Type 2 Olmadan ML Özellik Mühendisliğinde Yaşanan Senaryo

Bir e-ticaret platformunda müşterinin terk etme (Churn) ihtimalini tahmin eden bir model geliştirdiğimizi varsayalım. 
*   Müşteri A, **15 Mayıs 2024** tarihinde alışveriş yapmıştır. O tarihte müşterinin harcamaları azdır ve "Standard" segmentindedir.
*   Müşteri A, **1 Haziran 2024** tarihinde büyük bir sipariş vererek "VIP" segmentine yükselmiştir.
*   Sistemimiz **SCD Type 1** kullanıyorsa, veritabanı 1 Haziran'da güncellenmiş ve eski "Standard" bilgisi ezilerek Müşteri A'nın segmenti her yerde "VIP" olarak işaretlenmiştir.

#### Hatalı Özellik Çıkarımı (SCD Type 1 / Leakage):
Modelimizi eğitmek için 15 Mayıs 2024 tarihli sipariş verisini çekiyoruz. Sistemde SCD Type 1 olduğu için sorgumuz bize Müşteri A'nın segmentini **"VIP"** olarak döndürür.

**Tehlike:** Model, 15 Mayıs'taki bir olayı tahmin ederken müşterinin 1 Haziran'da kazandığı "VIP" statüsünü öğrenmiş olur. Müşteri henüz VIP değilken model onu VIP sanarak tahmin yürütür. Bu duruma **Time-Travel Leakage (Zaman Yolculuğu Sızıntısı)** denir.

---

### 5. SCD Type 2 Çözümü ve Point-In-Time Correctness

Aynı senaryoda **SCD Type 2** kullanıldığında özellik çıkarma sorgusu şu şekilde yazılır:

    SELECT f.order_id, f.customer_id, f.order_date, d.segment
    FROM fact_orders f
    JOIN dim_customer_scd2 d 
      ON f.customer_id = d.customer_id
     WHERE f.order_date >= d.valid_from 
       AND f.order_date < d.valid_to;

Bu sorgu sayesinde, 15 Mayıs 2024 tarihli sipariş için `valid_from: 2023-01-01` ve `valid_to: 2024-05-31` aralığına düşen **"Standard"** segmenti eşleşir. Müşterinin bugünkü VIP olmasının geçmişe sızması kesin olarak engellenir.

ML literatüründe buna **Point-In-Time Correctness (Zamanda Noktasal Doğruluk)** denir. Model, tahmin yaptığı andaki dünyada sadece ne biliyorsa onunla eğitilmiş olur.

---

### 6. Sonuç ve Mühendislik Prensipleri

1.  **SCD Type 1 ML İçin Zehirdir:** Geçmiş kayıtların üzerine yazılan veri ambarı mimarilerinde güvenilir ML özellikleri türetmek imkansızdır.
2.  **Point-In-Time Join Zorunluluğu:** Özellik mağazaları (Feature Store) ve analitik katmanlar, geçmiş tarihli eğitim verisi hazırlarken SCD Type 2 tabloları üzerinden tarih aralığı koşuluyla (`BETWEEN valid_from AND valid_to`) birleştirme yapmalıdır.
3.  **Üretim-Eğitim Uyumsuzluğu (Training-Serving Skew):** SCD Type 2 kullanılmadığında model eğitimde geleceği gördüğü için üretime geçtiğinde canlı verideki müşterinin geçmiş durumunu anlayamaz ve tahmin performansı dramatik şekilde çöker.

Sonuç olarak; SCD Type 2 mimarisi sadece bir veritabanı düzenleme tercihi değil, güvenilir ve üretime hazır makine öğrenmesi modelleri oluşturmanın en temel şartıdır.