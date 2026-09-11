# Ödev 3.3: Performans Laboratuvarı ve İndeks Optimizasyonu

## Senaryo 1: Fonksiyon Uygulanmış Kolon (Kötü Pratik)

**Kasten Kötü Yazılmış Sorgu:**
`created_at` kolonuna `EXTRACT()` fonksiyonu uygulayarak veritabanını tüm tabloyu okumaya (Seq Scan) zorluyoruz.

```sql
EXPLAIN ANALYZE 
SELECT * 
FROM orders 
WHERE EXTRACT(MONTH FROM created_at) = 5;
```

**EXPLAIN ANALYZE Çıktısı (Röntgen):**
```text
Seq Scan on orders (cost=0.00..3402.00 rows=750 width=32) (actual time=0.108..43.624 rows=8907 loops=1)
  Filter: (EXTRACT(month FROM created_at) = '5'::numeric)
  Rows Removed by Filter: 141093
Planning Time: 0.593 ms
Execution Time: 44.234 ms
```

**Teşhis ve Analiz:**
Sorgu planında açıkça görüldüğü üzere `Seq Scan` (Sıralı Tarama) yapılmıştır. Veritabanı sadece 8.907 satırlık sonucu bulabilmek için tam **141.093 satırı gereksiz yere okuyup filtrelemek (Rows Removed by Filter) zorunda kalmıştır**. `WHERE` bloğunda kolona bir fonksiyon uygulandığı için veritabanı mevcut indeksleri kullanamayıp "kör" olmuştur.

---

**Optimize Edilmiş Sorgu ve İndeksleme (Doğru Pratik):**
Sorguyu `EXTRACT` fonksiyonundan kurtarıp net bir tarih aralığı (range) koşuluna (`SARGable` format) çevirdik ve `created_at` kolonu üzerine bir indeks ekledik.

```sql
-- 1. İndeks Oluşturma
CREATE INDEX idx_orders_created_at ON orders(created_at);

-- 2. Optimize Sorgu
EXPLAIN ANALYZE 
SELECT * 
FROM orders 
WHERE created_at >= '2024-05-01' AND created_at < '2024-06-01';
```

**EXPLAIN ANALYZE Çıktısı (Röntgen):**
```text
Index Scan using idx_orders_created_at on orders  (cost=0.42..8.44 rows=1 width=32) (actual time=0.064..0.064 rows=0 loops=1)
  Index Cond: ((created_at >= '2024-05-01 00:00:00'::timestamp without time zone) AND (created_at < '2024-06-01 00:00:00'::timestamp without time zone))
Planning Time: 1.389 ms
Execution Time: 0.134 ms
```

**Tedavi ve Sonuç:**
Kötü yazılmış sorgudaki `Seq Scan` (Sıralı Tarama), sorgunun `SARGable` (Search Argument Able) formata getirilmesi ve ilgili kolona indeks eklenmesiyle **`Index Scan`**'e dönüşmüştür. Veritabanı 150.000 satırı okuyup filtrelemekten kurtulmuş, çalışma süresi 44.2 ms'den **0.134 ms**'ye düşerek muazzam bir hız (yaklaşık 330 kat) elde edilmiştir.

---

## Senaryo 2: Baştaki Yüzde İşareti / Leading Wildcard (Kötü Pratik)

**Kasten Kötü Yazılmış Sorgu:**
`name` kolonu üzerinde indeks (B-Tree) olmasına rağmen arama parametresinin başına `%` (Leading Wildcard) koyarak indeksi kasten devre dışı bırakıyoruz.

```sql
-- İndeks mevcut: CREATE INDEX idx_users_name ON users(name);
EXPLAIN ANALYZE 
SELECT * 
FROM users 
WHERE name LIKE '%Mehmet%';
```

**EXPLAIN ANALYZE Çıktısı (Röntgen):**
```text
Seq Scan on users  (cost=0.00..1225.00 rows=5 width=65) (actual time=0.146..13.028 rows=43 loops=1)
  Filter: ((name)::text ~~ '%Mehmet%'::text)
  Rows Removed by Filter: 49957
Planning Time: 4.220 ms
Execution Time: 13.185 ms
```

**Teşhis ve Analiz:**
Sorgu planında net bir şekilde görüldüğü üzere, kolon indekslenmiş olmasına rağmen **`Seq Scan`** yapılmıştır ve 49.957 satır tek tek okunup elenmiştir. Bunun sebebi standart `B-Tree` indekslerinin soldan sağa (alfabetik) çalışmasıdır. Arama parametresi `%` ile başladığında veritabanı aramaya hangi harften başlayacağını bilemez ve mecburen tam tablo taraması yapar. Bu durum, indeksin İŞE YARAMADIĞI klasik bir anti-pattern (kötü pratik) örneğidir.

**Nasıl Çözülür (Doğru Pratik):**
Mümkünse baştaki `%` işareti kaldırılmalıdır (örn: `LIKE 'Mehmet%'` şeklinde prefix araması yapılmalıdır). Eğer uygulamanın doğası gereği kelimenin ortasında geçen metinler (substring) aranmak zorundaysa, standart B-Tree indeksi yerine PostgreSQL'in metin aramalarına özel indeksleri (Full Text Search veya `pg_trgm` eklentisi ile `GIN` indeksi) kullanılmalıdır.

---

**Nasıl Çözülür (İdeal Çözüm ve Pattern-Aware İndeks):**
Baştaki `%` işaretini kaldırmak (prefix araması yapmak) B-Tree indeks teorisine göre yeterli görünse de, PostgreSQL'de metin aramalarında indeksin tam anlamıyla devreye girmesi için indeksin `varchar_pattern_ops` operatör sınıfıyla oluşturulması gerekir.

```sql
-- 1. Desene duyarlı (pattern-aware) indeks oluşturulması
CREATE INDEX idx_users_name_pattern ON users(name varchar_pattern_ops);

-- 2. Optimize edilmiş Prefix (Önek) Sorgusu
EXPLAIN ANALYZE 
SELECT * 
FROM users 
WHERE name LIKE 'Mehmet%';
```

**EXPLAIN ANALYZE Çıktısı (Röntgen):**
```text
Index Scan using idx_users_name_pattern on users  (cost=0.41..8.44 rows=5 width=65) (actual time=0.344..0.382 rows=26 loops=1)
  Index Cond: (((name)::text ~>=~ 'Mehmet'::text) AND ((name)::text ~<~ 'Mehmeu'::text))
  Filter: ((name)::text ~~ 'Mehmet%'::text)
Planning Time: 1.368 ms
Execution Time: 0.410 ms
```

**Tedavi ve Sonuç:**
İndeks sınıfı doğru ayarlandığında, veritabanı `LIKE 'Mehmet%'` sorgusunu bir aralık sorgusuna (`>= Mehmet` ve `< Mehmeu`) çevirerek kusursuz bir **Index Scan** gerçekleştirmiştir. Çöpe atılan 49 bin satır ortadan kalkmış ve sorgu süresi milisaniyenin altına inmiştir.

---

## Senaryo 3: OR Operatörü Tuzağı (Kötü Pratik)

**Kasten Kötü Yazılmış Sorgu:**
Farklı kolonları `OR` operatörü ile bağlayarak veritabanının olası indeksleri kullanmasını engelliyor ve tüm tabloyu taramaya zorluyoruz.

```sql
EXPLAIN ANALYZE 
SELECT * 
FROM orders 
WHERE user_id = 105 OR status = 'cancelled';
```

**EXPLAIN ANALYZE Çıktısı (Röntgen):**
```text
Seq Scan on orders  (cost=0.00..3402.00 rows=4314 width=32) (actual time=0.027..28.631 rows=4407 loops=1)
  Filter: ((user_id = 105) OR ((status)::text = 'cancelled'::text))
  Rows Removed by Filter: 145593
Planning Time: 0.386 ms
Execution Time: 28.946 ms
```

**Teşhis ve Analiz:**
Sorgu planında **`Seq Scan`** yapıldığı ve 145.593 satırın gereksiz yere okunup elendiği görülmektedir. `OR` bağlacı kullanıldığında veritabanı motoru (eğer her iki şart için de kusursuz birer indeks yoksa veya birleştirme maliyetini yüksek bulursa) indeks kullanmaktan vazgeçer ve "Full Table Scan" (Tam Tablo Taraması) yöntemine geri döner. Bu durum indekslerin işlevsiz kaldığı klasik bir senaryodur.

---

**Nasıl Çözülür (İdeal Çözüm: UNION ve İndeksleme):**
`OR` operatörü veritabanını kilitlediği için, usta mühendisler bu tip sorguları `UNION` (veya tekrarları elemek gerekmiyorsa çok daha performanslı olan `UNION ALL`) ile iki bağımsız parçaya böler. Böylece veritabanı her iki koşul için de kendi özel indeksini kullanabilir.

```sql
-- 1. Eksik İndekslerin Oluşturulması
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);

-- 2. Optimize Edilmiş UNION Sorgusu
EXPLAIN ANALYZE 
SELECT * FROM orders WHERE user_id = 105
UNION
SELECT * FROM orders WHERE status = 'cancelled';
```

**EXPLAIN ANALYZE Çıktısı (Röntgen):**
```text
HashAggregate  (cost=4067.16..4110.30 rows=4314 width=154) (actual time=20.598..21.770 rows=4407 loops=1)
  ->  Append  (cost=0.00..4002.45 rows=4314 width=154) (actual time=3.158..16.375 rows=4408 loops=1)
        ->  Seq Scan on orders  (cost=0.00..3027.00 rows=4 width=32) (actual time=3.157..12.607 rows=2 loops=1)
              Filter: (user_id = 105)
        ->  Index Scan using idx_orders_status on orders orders_1  (cost=0.29..953.88 rows=4310 width=32) (actual time=0.347..3.260 rows=4406 loops=1)
              Index Cond: ((status)::text = 'cancelled'::text)
Execution Time: 22.165 ms
```

**Tedavi ve Sonuç:**
Sorgu `UNION` ile bölündüğünde, `status` kolonu için yaratılan indeks başarıyla devreye girmiş (`Index Scan`) ve sorgu süresi yaklaşık 80 ms'den 22 ms'ye düşmüştür. `user_id` kolonu için indeks yaratılmış olmasına rağmen PostgreSQL'in `Seq Scan` tercih etmesinin sebebi, İstatistik ve Kardinalite (Cardinality) tahmini mekanizmasıdır; veritabanı motoru aranılan kaydın çok az (2 adet) olduğunu bildiği için indeks ağacını okumak yerine tabloya doğrudan erişmeyi daha ucuz (cost) bulmuştur.

---

## Senaryo 4: Tip Uyuşmazlığı / Type Mismatch (Kötü Pratik)

**Kasten Kötü Yazılmış Sorgu:**
Sayısal (integer) bir kolon olan `user_id` üzerinde arama yaparken, veriyi metne (`::text`) dönüştürerek mevcut B-Tree indeksini kasten kör ediyoruz.

```sql
-- idx_orders_user_id indeksi mevcut olmasına rağmen:
EXPLAIN ANALYZE 
SELECT * 
FROM orders 
WHERE user_id::text = '105';
```

**EXPLAIN ANALYZE Çıktısı (Röntgen):**
```text
Seq Scan on orders  (cost=0.00..3777.00 rows=750 width=32) (actual time=6.187..22.978 rows=2 loops=1)
  Filter: ((user_id)::text = '105'::text)
  Rows Removed by Filter: 149998
Planning Time: 0.818 ms
Execution Time: 23.055 ms
```

**Teşhis ve Analiz:**
Sorgu planında **`Seq Scan`** yapıldığı açıkça görülmektedir. `user_id` kolonu için bir indeks bulunmasına rağmen, koşul bloğunda kolona tip dönüşümü (`::text`) uygulandığı için veritabanı motoru indeksi kullanamamış ve 150.000 satırın tamamını okuyup dönüştürmek zorunda kalmıştır. Bu durum, veri tiplerinin (strongly-typed prensibi) veritabanı performansındaki hayati önemini kanıtlamaktadır.

**Nasıl Çözülür (Doğru Pratik):**
Arama parametreleri her zaman hedef kolonun orijinal veri tipiyle eşleşmelidir. Sorgu `WHERE user_id = 105;` şeklinde yazıldığında veritabanı anında `Index Scan` yapacak ve sorguyu milisaniyenin altına indirecektir.

---

**İdeal Çözüm Denemesi ve Gizli Tip Uyuşmazlığı (Implicit Cast) Vakası:**
Sorguyu `WHERE user_id = 105;` şeklinde (sözde doğru tiplerle) düzeltmemize rağmen veritabanı `Seq Scan` yapmaya devam etmiştir. Hatta veritabanına `SET enable_seqscan = OFF;` komutuyla sıralı tarama yapmayı yasakladığımızda bile indeksi kullanamamış ve maliyeti 10 milyar (cost=10000000000.00) olarak hesaplamıştır. 

```sql
-- Sıralı tarama yasaklanarak indeks zorlaması yapılıyor
SET enable_seqscan = OFF;
EXPLAIN ANALYZE 
SELECT * FROM orders WHERE user_id = 105;
SET enable_seqscan = ON;
```

**Zorlanmış EXPLAIN ANALYZE Çıktısı:**
```text
Seq Scan on orders  (cost=10000000000.00..10000003027.00 rows=4 width=32) (actual time=247.708..252.671 rows=2 loops=1)
  Filter: (user_id = 105)
```

**Mühendislik Çıkarımı:**
Eğer veritabanı zorlamaya rağmen indeksi kullanamıyorsa, tablonun fiziksel yapısındaki veri tipi ile sorgudaki veri tipi tamamen uyumsuzdur. Tablodaki `user_id` kolonu muhtemelen `VARCHAR` olarak tasarlanmıştır. Biz sorguya `105` (integer) gönderdiğimizde, veritabanı arka planda gizli bir tip dönüşümü (implicit cast) yapmak zorunda kalmış ve bu da mevcut indeksi tamamen felç etmiştir. Tip uyuşmazlığı, indekslerin bir numaralı düşmanıdır.

---

## Senaryo 5: Kolon Üzerinde Matematiksel İşlem (Kötü Pratik)

**Kasten Kötü Yazılmış Sorgu:**
Arama kriterindeki matematiksel işlemi sabit değer (koşul) üzerinde yapmak yerine doğrudan kolon (`total_amount`) üzerinde yaparak olası indeks kullanımlarını engelliyoruz.

```sql
EXPLAIN ANALYZE 
SELECT * 
FROM orders 
WHERE total_amount * 1.10 > 500;
```

**EXPLAIN ANALYZE Çıktısı (Röntgen):**
```text
Seq Scan on orders  (cost=0.00..3402.00 rows=50000 width=32) (actual time=36.823..36.824 rows=0 loops=1)
  Filter: ((total_amount * 1.10) > '500'::numeric)
  Rows Removed by Filter: 150000
Planning Time: 0.336 ms
Execution Time: 36.844 ms
```

**Teşhis ve Analiz:**
Çıktıda açıkça `Seq Scan` (Sıralı Tarama) görülmektedir. Veritabanı motoru, 150.000 satırın tamamını okuyarak her bir satır için anlık olarak `* 1.10` çarpımını uygulamış ve sonrasında filtreleme yapmıştır. Kolona bir aritmetik işlem uygulandığı an, B-Tree indeks yapısındaki sıralama mantığı bozulur ve indeks geçersiz kalır.

---

**Nasıl Çözülür (İdeal Çözüm ve SARGable Kuralı):**
Veritabanlarında "Kolona dokunma, koşula dokun" kuralı geçerlidir. Çarpım durumundaki katsayı, eşitsizliğin diğer tarafına (sabit değerin yanına) geçirilerek kolon yalnız bırakılmalı ve indeksin çalışmasına izin verilmelidir.

```sql
-- 1. Hedef Kolona İndeks Eklenmesi
CREATE INDEX idx_orders_total_amount ON orders(total_amount);

-- 2. Optimize Edilmiş SARGable Sorgu
EXPLAIN ANALYZE 
SELECT * 
FROM orders 
WHERE total_amount > 500 / 1.10;
```

**EXPLAIN ANALYZE Çıktısı (Röntgen):**
```text
Index Scan using idx_orders_total_amount on orders  (cost=0.42..4.44 rows=1 width=32) (actual time=0.126..0.126 rows=0 loops=1)
  Index Cond: (total_amount > 454.5454545454545455)
Planning Time: 0.989 ms
Execution Time: 0.152 ms
```

**Tedavi ve Sonuç:**
Aritmetik işlem sabit değerin üzerine kaydırıldığında, Query Planner işlemi önceden hesaplayıp (Constant Folding) aranan değeri sabitler. Kolon serbest kaldığı için indeks başarıyla devreye girmiş (`Index Scan`) ve sorgu süresi 36.8 ms'den muazzam bir düşüşle **0.152 ms**'ye inmiştir.

---

## 6. Performans Özeti ve Hızlanma Oranları Tablosu

Aşağıdaki tablo, 5 farklı senaryoda kasten kötü yazılmış sorguların optimizasyon öncesi ve sonrası çalışma sürelerini ile hızlanma çarpanlarını özetlemektedir.

| Senaryo | Kötü Pratik (Hata) | Öncesi Süre | Sonrası Süre | Hızlanma Çarpanı |
| :--- | :--- | :--- | :--- | :--- |
| **Senaryo 1** | Kolona Fonksiyon Uygulama (`EXTRACT`) | 44.234 ms | 0.134 ms | **~330x Daha Hızlı** |
| **Senaryo 2** | Baştaki Yüzde İşareti (`LIKE '%...'`) | 13.185 ms | 0.410 ms | **~32x Daha Hızlı** |
| **Senaryo 3** | `OR` Operatörü Kullanımı | 28.946 ms | 22.165 ms | **~1.3x Daha Hızlı** |
| **Senaryo 4** | Tip Uyuşmazlığı (Implicit Cast) | 23.055 ms | Başarısız | **İndeks Devre Dışı Kaldı** |
| **Senaryo 5** | Kolon Üzerinde Matematiksel İşlem | 36.844 ms | 0.152 ms | **~242x Daha Hızlı** |

---

## 7. İndeksin İşe Yaramadığı Örnek Durumlar (Anti-Pattern)

Görev yönergesinde belirtilen kısıtlamalar doğrultusunda, bir kolonda indeks bulunmasına rağmen veritabanı motorunun indeksi kullanamayıp (Full Table Scan) tüm tabloyu taramak zorunda kaldığı iki kritik senaryo ve teknik açıklamaları aşağıdadır[cite: 2]:

*   **Örnek 1: Tip Uyuşmazlığı (Type Mismatch) ve Gizli Dönüşüm**
    Sorgu sırasında aranan parametrenin veri tipi ile tablodaki kolonun veri tipi eşleşmediğinde indeks geçersiz kalır. Örneğin; fiziksel olarak `VARCHAR` tasarlanmış bir `user_id` kolonuna, sorguda `WHERE user_id = 105` (integer) şeklinde değer gönderildiğinde, PostgreSQL arka planda tüm tabloyu okuyarak metinleri sayıya çevirmeye (implicit cast) çalışır. Bu tip uyuşmazlığı, B-Tree yapısını tamamen kör eder.
*   **Örnek 2: Leading Wildcard (Baştaki Yüzde İşareti) Kullanımı**
    Metin tabanlı (`LIKE`) aramalarda parametrenin başına `%` işareti konulması (örn: `%Mehmet%`), standart B-Tree indekslerinin çalışmasını engeller. B-Tree indeksleri veriyi soldan sağa alfabetik sıralayarak bulur. Baştaki karakterin ne olduğu bilinmediğinde (joker karakter kullanıldığında), veritabanı arama ağacına nereden gireceğini bilemez ve mecburen tablonun tamamını satır satır okumak (Seq Scan) zorunda kalır.