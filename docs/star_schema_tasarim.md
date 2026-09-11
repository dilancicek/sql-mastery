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

*   **Eski Kayıt:** `is_current` bayrağı `false` yapılmış ve `valid_to` kolonuna değişim anının zaman damgası işlenmiştir.
*   **Yeni Kayıt:** 'Premium' segmentiyle yeni bir satır oluşturulmuş, `is_current` bayrağı `true` yapılarak güncel kayıt olarak sisteme dahil edilmiştir.

![SCD Type 2 Test Kanıtı](scd_test_kaniti.png)

Bu yapı sayesinde makine öğrenmesi modelleri geçmiş tarihteki özellikleri çekerken "Veri Sızıntısı (Data Leakage)" problemi yaşanmayacaktır.

---

## 3. Sorgu Performansı ve Okunabilirlik Karşılaştırması

Veri ambarı tasarımımızın (Star Schema) analitik sorguları ne kadar basitleştirdiğini kanıtlamak için karmaşık bir iş sorusu ele alınmıştır.

**İş Sorusu:** *"Premium segmentteki müşterilerin, 'Elektronik' kategorisindeki ürünlere yaptıkları günlük toplam harcamalar nelerdir?"*

### A) Mevcut Operasyonel Sistem (OLTP) Yaklaşımı
Normalleştirilmiş (3NF) yapıda bu veriyi çekmek için çok sayıda tabloyu birleştirmek (JOIN) ve sistemi yormak gerekir:

```sql
SELECT 
    DATE(o.created_at) AS siparis_tarihi, 
    SUM(oi.quantity * oi.unit_price) AS toplam_harcama
FROM users u
JOIN orders o ON u.id = o.user_id
JOIN order_items oi ON o.id = oi.order_id
JOIN products p ON oi.product_id = p.id
JOIN categories c ON p.category_id = c.id
WHERE u.segment = 'Premium' 
  AND c.name = 'Elektronik'
GROUP BY DATE(o.created_at)
ORDER BY siparis_tarihi;
```


### B) Star Schema (Analitik) Yaklaşımı
Tasarladığımız boyut (Dimension) ve gerçek (Fact) tabloları sayesinde, aracı tablolara (kategori vb.) gerek kalmadan sorgu doğrudan hedef odaklı ve çok daha performanslı çalışır. Ayrıca `is_current` bayrağı ile veri sızıntısı önlenir:

```sql
SELECT 
    dd.full_date AS siparis_tarihi, 
    SUM(foi.total_amount) AS toplam_harcama
FROM fct_order_items foi
JOIN dim_customer dc ON foi.customer_sk = dc.customer_sk
JOIN dim_product dp ON foi.product_sk = dp.product_sk
JOIN dim_date dd ON foi.date_sk = dd.date_sk
WHERE dc.segment = 'Premium' 
  AND dc.is_current = TRUE 
  AND dp.category_name = 'Elektronik'
GROUP BY dd.full_date
ORDER BY siparis_tarihi;
```

**Sonuç:** Star Schema tasarımı sayesinde JOIN sayıları azalmış, hesaplamalar (`total_amount`) önceden yapılmış ve veri sızıntısı riski ortadan kaldırılmıştır.
