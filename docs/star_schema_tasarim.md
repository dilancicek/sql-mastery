# Ödev 3.4: Analitik Katman ve Star Schema Tasarımı

Bu dokümanda OLTP (Operasyonel) veritabanımızdan, analitik sorgular (OLAP) için optimize edilmiş Yıldız Şema (Star Schema) yapısına geçiş adımları tasarlanmıştır.

## 1. Grain (Tane) Tanımları
Star Schema tasarımının en kritik kuralı, her tablonun tek bir satırının (grain) neyi ifade ettiğinin çok net olarak belirlenmesidir.

**Fact (Gerçek) Tabloları:**
*   **fct_orders:** Bir satır, bir kullanıcının sepeti onaylayıp sistemde oluşturduğu **tek bir sipariş işlemini (order)** temsil eder.
*   **fct_order_items:** Bir satır, onaylanan bir siparişin içindeki **tek bir ürün kalemini (line item)** temsil eder. (Örn: Bir siparişte 3 farklı ürün alındıysa, bu tabloda o siparişe ait 3 ayrı satır oluşur).

**Dimension (Boyut) Tabloları:**
*   **dim_customer:** Bir satır, sistemimize kayıtlı **tek bir müşterinin belirli bir tarih aralığındaki profilini** temsil eder. (SCD Type 2 ile geçmişteki değişimler de ayrı satırlar olarak tutulacaktır).
*   **dim_product:** Bir satır, katalogda satışa sunulan **tek bir spesifik ürünü** temsil eder.
*   **dim_date:** Bir satır, analitik takvimdeki **tek bir günü** (örneğin: 11 Eylül 2026) temsil eder.

---

## 2. Test Sonuçları ve SCD Type 2 Kanıtı

DBeaver üzerinde yapılan testlerde, Idempotent yükleme scriptinin başarılı bir şekilde çalıştığı doğrulanmıştır. 101 ID'li müşterinin segmenti 'Standard' değerinden 'Premium' değerine güncellendiğinde sistemin verdiği tepki aşağıdadır:

Idempotent Yükleme SQL Scripti:

-- 1. Değişen kayıtların eski versiyonlarını pasife çek
```sql
UPDATE dim_customer dc
SET is_current = FALSE,
    valid_to = CURRENT_TIMESTAMP
FROM staging_customers sc
WHERE dc.customer_id = sc.customer_id
  AND dc.is_current = TRUE
  AND dc.segment != sc.segment;
```

-- 2. Yeni veya güncellenmiş kayıtları sisteme aktif olarak ekle
```sql
INSERT INTO dim_customer (customer_id, segment, valid_from, valid_to, is_current)
SELECT sc.customer_id, sc.segment, CURRENT_TIMESTAMP, '9999-12-31', TRUE
FROM staging_customers sc
LEFT JOIN dim_customer dc 
  ON sc.customer_id = dc.customer_id AND dc.is_current = TRUE
WHERE dc.customer_id IS NULL OR dc.segment != sc.segment;
```

* Eski Kayıt: `is_current` bayrağı `false` yapılmış ve `valid_to` kolonuna değişim anının zaman damgası işlenmiştir.
* Yeni Kayıt: 'Premium' segmentiyle yeni bir satır oluşturulmuş, `is_current` bayrağı `true` yapılarak güncel kayıt olarak sisteme dahil edilmiştir.

![SCD Type 2 Test Kanıtı](scd_test_kaniti.png)

Bu yapı sayesinde makine öğrenmesi modelleri geçmiş tarihteki özellikleri çekerken "Veri Sızıntısı (Data Leakage)" problemi yaşanmayacaktır.

---

## 3. Sorgu Performansı ve Okunabilirlik Karşılaştırması (10 İş Sorusu)

Veri ambarı tasarımımızın (Star Schema) analitik sorguları ne kadar basitleştirdiğini ve hızlandırdığını kanıtlamak için 10 farklı iş sorusu hem OLTP (3NF) hem de Star Schema mimarisinde çalıştırılmıştır.

### A) Okunabilirlik ve Kod Karmaşıklığı Karşılaştırması
* **OLTP Yaklaşımı:** Normalleştirilmiş (3NF) yapıda veriyi çekmek için çok sayıda tabloyu (`users`, `orders`, `order_items`, `products`, `categories`) birbirine JOIN'lemek ve `DATE_TRUNC`, `EXTRACT` gibi maliyetli fonksiyonlar kullanmak gerekmiştir. Bu durum kod okunabilirliğini ciddi ölçüde düşürmekte ve sorgu karmaşıklığını artırmaktadır.
* **Star Schema Yaklaşımı:** Denormalize fact tabloları ve önceden hesaplanmış dimension tabloları (`dim_date`, `dim_product`, `dim_customer` vb.) sayesinde JOIN sayıları minimuma inmiş; sorgular hedefe yönelik, yalın ve okunabilir bir hâl almıştır.

### B) Performans Test Sonuçları (Sorgu Süreleri)
PostgreSQL (DBeaver) üzerinde gerçekleştirilen milisaniye bazlı gerçek yürütme süreleri karşılaştırmalı olarak aşağıdadır:

| No | İş Sorusu (Query) | OLTP Süresi | Star Schema Süresi | Performans Artışı |
| :--- | :--- | :--- | :--- | :--- |
| **1** | Kategori Bazında Günlük Toplam Ciro | 26 ms | 7 ms | ~3.7 Kat Daha Hızlı |
| **2** | Müşteri Durumuna Göre Toplam Harcama | 1102 ms | 4 ms | ~275 Kat Daha Hızlı |
| **3** | Hafta Sonu vs Hafta İçi Performansı | 624 ms | 74 ms | ~8.4 Kat Daha Hızlı |
| **4** | Ürün Bazında İptal/İade Oranları | 394 ms | 4 ms | ~98.5 Kat Daha Hızlı |
| **5** | İlk ve İkinci Sipariş Harcama Farkı | 404 ms | 4 ms | ~101 Kat Daha Hızlı |
| **6** | Aylık Bazda Büyüme Oranı (MoM) | 518 ms | 7 ms | ~74 Kat Daha Hızlı |
| **7** | En Çok Satan İlk 5 Ürün ve Kategorisi | 510 ms | 7 ms | ~72 Kat Daha Hızlı |
| **8** | Son 7 Günlük Hareketli Toplam (Rolling) | 455 ms | 5 ms | ~91 Kat Daha Hızlı |
| **9** | En Değerli İlk 10 Müşteri (LTV) | 762 ms | 4 ms | ~190.5 Kat Daha Hızlı |
| **10** | Kategori Bazında İptal Edilen Ciro | 28 ms | 8 ms | ~3.5 Kat Daha Hızlı |

### C) Genel Değerlendirme
Test sonuçlarından da net bir şekilde görüleceği üzere; özellikle çoklu JOIN gerektiren, gruplama yapılan ve pencere fonksiyonları (`Window Functions`) içeren karmaşık analitik sorgularda Star Schema mimarisi, OLTP sistemine kıyasla **3.5 kattan 275 kata varan** oranlarda üstün performans göstermiştir.

## 4. Performans Doğrulaması ve Execution Plan Analizi (Ek Değerlendirme)

### 4.1. Veri Yükleme (ETL) ve Satır Sayısı Doğrulaması
İlk testlerde tespit edilen aşırı düşük sorgu sürelerinin (4-7 ms) veri eksikliğinden kaynaklanmadığını ve ETL işleminin başarılı olduğunu doğrulamak için OLTP ile Star Schema satır sayıları karşılaştırılmıştır:

```sql
-- OLTP Tabloları
SELECT COUNT(*) FROM orders;          -- Sonuç: 150.000
SELECT COUNT(*) FROM order_items;     -- Sonuç: 375.684

-- Star Schema (Fact) Tabloları
SELECT COUNT(*) FROM fct_orders;      -- Sonuç: 150.000
SELECT COUNT(*) FROM fct_order_items; -- Sonuç: 375.684
```

**Bulgu:** `fct_orders` ve `fct_order_items` tablolarındaki satır sayıları OLTP kaynağıyla birebir eşleşmektedir. Testler veri kümelerinin alt parçalarında (subset) veya boş tablolar üzerinde değil, %100 tam veri seti üzerinde gerçekleştirilmiştir.

### 4.2. Gerçek Yük Altında Sorgu Analizi ve Bellek (Buffer) Metrikleri
DBeaver'ın gösterdiği istemci (client) arayüz gecikmelerinden arındırılmış, sunucu tarafındaki gerçek iş yükünü ve okunan sayfa (page) sayısını ölçmek için `EXPLAIN (ANALYZE, BUFFERS)` kullanılmıştır.

**Test Sorgusu:** Son 3 aylık iptal edilen siparişlerin günlük bazda cirosu

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT 
    d.full_date,
    SUM(f.total_amount) as daily_cancelled_revenue
FROM fct_orders f
JOIN dim_date d ON f.date_sk = d.date_sk
WHERE f.order_status = 'cancelled' 
  AND d.full_date >= '2024-06-08'
GROUP BY d.full_date
ORDER BY d.full_date DESC;
```

**Execution Plan Çıktısı (Özet):**
```text
Sort (cost=3081.33..3083.15 rows=731 width=36) (actual time=26.762..26.804 rows=724 loops=1)
  Sort Key: d.full_date DESC
  Sort Method: quicksort  Memory: 47kB
  Buffers: shared hit=1112
  -> HashAggregate  (cost=3037.42..3046.55 rows=731 width=36) (actual time=26.249..26.446 rows=724 loops=1)
        Group Key: d.full_date
        Batches: 1  Memory Usage: 297kB
        Buffers: shared hit=1109
        -> Hash Join  (cost=24.28..3014.42 rows=4600 width=7) (actual time=0.466..23.324 rows=4406 loops=1)
              Hash Cond: (f.date_sk = d.date_sk)
              Buffers: shared hit=1109
              -> Seq Scan on fct_orders f  (cost=0.00..2978.00 rows=4600 width=7) (actual time=0.032..21.124 rows=4406 loops=1)
                    Filter: ((order_status)::text = 'cancelled'::text)
                    Rows Removed by Filter: 145594
                    Buffers: shared hit=1103
Planning Time: 71.528 ms
Execution Time: 27.315 ms
```

### 4.3. Mühendislik Çıkarımları
* **Filtreleme ve İş Yükü:** Sorgu boş bir tabloyu değil, 150.000 kayıtlık tabloyu taramış ve iptal edilmeyen 145.594 kaydı başarıyla filtrelemiştir (`Rows Removed by Filter: 145594`).
* **Execution Time (Gerçek Süre):** İşlemin saf veritabanı yürütme süresi **27.3 ms** olarak ölçülmüştür.
* **Buffer (Bellek) Tüketimi:** Star Schema üzerinde gerçekleştirilen bu analiz için toplamda yalnızca **1112 sayfa (shared hit=1112)** bellekten okunmuştur. Disk okuması (read) yapılmamış, veri doğrudan RAM üzerinden hızlıca getirilmiştir. Bu düşük buffer sayısı, mimarinin analitik okumalar için yüksek oranda optimize edildiğinin en büyük fiziksel kanıtıdır.