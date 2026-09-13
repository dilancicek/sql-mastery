# Bölüm 3.7 SQL ve Veri Modelleme Kontrol Soruları

### 1. LEFT JOIN sonrası `WHERE b.col IS NOT NULL` yazmak ne yapar, INNER JOIN'den farkı nedir?
`LEFT JOIN` kullandığınızda, sol tablodaki tüm satırlar getirilir; sağ tabloda eşleşmeyen satırlar için sağ tablonun kolonları `NULL` olarak doldurulur. Ancak sorgunun sonuna `WHERE b.col IS NOT NULL` (sağ tablodaki bir kolona) şartı eklediğinizde, mantıksal olarak **sağ tabloyla eşleşmeyen (NULL gelen) tüm satırları filtrelemiş olursunuz**. 

* **Pratik Etkisi:** Bu işlem `LEFT JOIN`'i fiilen bir `INNER JOIN`'e dönüştürür.
* **INNER JOIN'den Farkı:** İşlevsel (sonuç kümesi) olarak bir farkı kalmaz. Ancak veritabanı sorgu optimize edicisi (Query Optimizer) bu durumu fark edip sorgu planını (Execution Plan) otomatik olarak `INNER JOIN`'e dönüştürse bile, bu kullanım bir **SQL Anti-Pattern**'dir. Kodu okuyan kişiye "LEFT JOIN yapılmak istendi ama sonra filtreyle bozularak INNER JOIN'e çevrildi" izlenimi verir, okunabilirliği düşürür.

---

### 2. `NOT IN` bir alt sorguda NULL varsa ne olur? Neden?
Alt sorgunun döndürdüğü sonuç kümesinde tek bir tane bile `NULL` değer varsa, `NOT IN` sorgusu **hiçbir satır döndürmez (boş küma döner)**.

* **Neden (Üç Değerli Mantık - Three-Valued Logic):** SQL'de mantıksal işlemler `TRUE`, `FALSE` ve `UNKNOWN` (Bilinmiyor) olarak 3 değer alır. `x NOT IN (1, 2, NULL)` ifadesi arka planda şu şekilde açılır:
  `(x <> 1) AND (x <> 2) AND (x <> NULL)`
  SQL'de `NULL` ile yapılan her karşılaştırma (`x <> NULL`) `UNKNOWN` sonucunu verir. `AND` zincirinde tek bir `UNKNOWN` veya `FALSE` bulunması, tüm `WHERE` şartının `TRUE` olmasını engeller. Bu yüzden veritabanı hiçbir satırı şartı sağlıyor kabul etmez.
* **Çözüm:** Bu tuzağa düşmemek için production kodunda `NOT IN` yerine her zaman `NOT EXISTS` kullanırız.

---

### 3. `COUNT(*)` ile `COUNT(column)` farkı hangi durumda tehlikeli sonuç verir?
`COUNT(*)` tablodaki veya gruptaki **toplam satır sayısını** sayarken; `COUNT(column)` sadece belirtilen **kolondaki `NULL` olmayan (NOT NULL) değerleri** sayar.

* **Tehlikeli Olduğu Durum:** İş analitiğinde bir gruptaki gerçek kayıt sayısı hesaplanmak istendiğinde, `NULL` içerebilecek bir kolon `COUNT(column)` şeklinde verilirse fark etmeden hatalı/eksik veri üretilir.
* **Somut Örnek:** Bir e-ticaret platformunda iptal edilen siparişlerin `shipping_date` (kargo tarihi) kolonu `NULL` olsun. 
  * `COUNT(*)` bize toplam sipariş sayısını verir.
  * `COUNT(shipping_date)` ise kargolanmamış/iptal siparişleri eler ve sadece kargolananları sayar. 
  Eğer dönüşüm oranı (conversion rate) veya ortalama hesaplarken paydada `COUNT(column)` kullanılırsa, `NULL` değerler elendiği için oranlar sahte bir şekilde yüksek çıkacaktır.

---

### 4. Bir join sonucunda satır sayım beklenenden 3 kat fazla — hangi 3 şeyi kontrol ederim?
Bir birleştirme (JOIN) işlemi sonrası satır patlaması (Fan-out problem) yaşanıyorsa inceleyeceğim ilk 3 nokta:

1. **Çoktan-Çoğa (Many-to-Many) İlişki Kontrolü (Grain İhlali):** Birleştirdiğim sağ veya sol tablodaki birleştirme anahtarının (Join Key) benzersiz (unique) olduğunu varsaymış olabilirim. Eğer iki tabloda da aynı anahtardan birden fazla varsa (1-to-N veya N-to-M), Kartezyen çarpım etkisi oluşur. İki tablonun da birleştirme kolonu bazında `COUNT(...) GROUP BY key HAVING COUNT(*) > 1` ile tekilliğini doğrularım.
2. **Eksik Join Koşulu (Missing Join Conditions):** Composite Key (birden fazla kolondan oluşan bileşik anahtar) yapısı olan bir tabloda bir birleştirme kuralını unutup unutmadığımı kontrol ederim (Örn: `tenant_id` veya `date` bilgisini join şartına eklemeyi unutmak).
3. **Filtrelenmemiş Geçmiş Kayıtlar (SCD Type 2 / Versiyonlama):** Birleştirilen boyut (dimension) tablosunda SCD Type 2 yapısı varsa ve ben `is_current = TRUE` veya `valid_to` filtrelerini eklemediysem, aynı müşterinin 3 farklı geçmiş versiyonu da sorguya dahil olur ve satır sayım tam 3 katına çıkar.

---

### 5. Window function ile `GROUP BY` arasındaki temel fark nedir?
Her iki yapı da veriyi gruplayarak agregasyon (SUM, AVG, COUNT vb.) yapmamızı sağlar, ancak verinin sunuluş biçimi tamamen farklıdır:

* **GROUP BY (Satırları Çökertir/Daraltır):** Sorguya giren satırları belirlenen kolonlara göre gruplar ve **grup başına tek bir satır** döndürür. Orijinal detay satırları (individual rows) kaybolur.
* **Window Function (Satır Detayını Korur):** Orijinal satır düzenini ve sayısını **kesinlikle bozmaz**. Agregasyon sonucunu, hesaplanan her bir satırın yanına yeni bir kolon olarak ekler. 
* **Özetle:** Bir sipariş tablosunda kullanıcı bazlı toplam harcamayı görürken aynı zamanda o siparişin tarihini ve tutarını yan yana görmek istiyorsak `GROUP BY` kullanamayız, `SUM() OVER(PARTITION BY user_id)` şeklinde Window Function kullanmak zorundayız.

---

### 6. Bir tabloya index eklemenin maliyeti nedir? (Sadece faydasını sayma.)
İndeksler okuma (`SELECT`) performansını muazzam artırsa da ücretsiz değillerdir; arkasında ciddi bir maliyet taşırlar:

1. **Yazma Performansı Kaybı (Write Overhead - INSERT/UPDATE/DELETE):** Tabloya yeni bir satır eklendiğinde veya var olan bir satır silindiğinde/güncellendiğinde, veritabanı sadece ana tabloyu değil, o tabloya bağlı **tüm B-Tree indeks ağaçlarını da yeniden dengelemek (rebalance) zorundadır**. Çok sayıda indeks olan tabloda `INSERT` işlemleri gözle görülür şekilde yavaşlar.
2.  **Depolama ve RAM Maliyeti (Storage & Buffer Pool Area):** İndeksler diskte ekstra yer kaplar. Bazen bir tablonun indeks boyutu, tablonun ham veri boyutunu geçebilir. Ayrıca veritabanı bu indeks bloklarını hızlı erişim için RAM'deki Buffer Pool alanına yükler ve RAM tüketimini artırır.
3. **Bakım ve İstatistik Maliyeti (Maintenance Overhead):** Zamanla indeksler parçalanır (fragmentation). Veritabanının düzenli olarak `VACUUM` veya `REINDEX` yapması gerekir. Ayrıca `ANALYZE` komutunun indeks istatistiklerini güncellemesi CPU yükü yaratır.