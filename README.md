# 🗄️ sql-mastery: Advanced SQL & Data Modeling Lab

Bu repo, operasyonel OLTP veritabanı tasarımından modern analitik OLAP (Star Schema) mimarilerine, 50 ileri düzey analitik sorgudan performans optimizasyonlarına (`EXPLAIN ANALYZE` & Indexing), DuckDB ile büyük veri analitiğinden derinlemesine araştırma ödevlerine ve mülakat kontrol sorularına kadar **Bölüm 3 (SQL & Veri Modelleme)** kapsamındaki tüm mühendislik çalışmalarını içermektedir.

---

## 📂 Repo Mimarisi ve İçerik

Proje, sürdürülebilir ve tekrar üretilebilir (reproducible) bir yapı kurmak amacıyla şu modüler hiyerarşiyle tasarlanmıştır:
* `docs/`: Tüm ödevlerin detaylı Markdown raporları ve DBeaver yürütme ekran görüntüleri (`images/`).
* `migrations/`: PostgreSQL şema kurulum ve migration scriptleri.
* `scripts/`: Sentetik veri üretimi ve otomasyon araçları.
* `src/`: Analitik sorgular ve Python/SQL test kodları.

---

## 🚀 Tamamlanan Ödevler ve Modüller

### 1. Ödev 3.1: OLTP Veritabanı Tasarımı ve Sentetik Veri Üretimi
* **Senaryo:** E-ticaret platformu için sıfırdan 3NF normalized OLTP şeması (`users`, `products`, `categories`, `orders`, `order_items`, `payments`, vb.).
* **Detaylar:** PK, FK, CHECK ve UNIQUE kısıtları; migration yapısı ve güç yasası (power law) dağılımına sahip gerçekçi sentetik veri üretimi.
* **Rapor:** [`docs/er_diyagrami.md`](docs/er_diyagrami.md)

### 2. Ödev 3.2: 50 İleri Düzey Analitik Sorgu Seti
* **Kapsam:** Window Functions (`ROW_NUMBER`, `LAG`, `LEAD`, `SUM OVER`), Gaps-and-Islands, Kohort Retention analizi, RFM segmentasyonu ve zaman serisi hesaplamalarını içeren 50 karmaşık iş sorusu.
* **Detaylar:** Her sorgu için iş yorumu, SQL kodu ve DBeaver sonuç ekran görüntüleri.
* **Rapor:** [`docs/50_analitik_sorgu.md`](docs/50_analitik_sorgu.md)

### 3. Ödev 3.3: Performans Laboratuvarı ve İndeksleme Optimizasyonu
* **Kapsam:** `EXPLAIN ANALYZE` okuma becerileri, Seq Scan vs Index Scan analizi.
* **Kritik Bulgular:** Kolon üzerine fonksiyon uygulama (`EXTRACT`) ve başı açık wildcard (`LIKE '%keyword'`) gibi indeksin "kör" olduğu anti-pattern'ler incelenmiş; SARGable sorgu yazımıyla **330 kata varan hızlanmalar** elde edilmiştir.
* **Rapor:** [`docs/performans_lab.md`](docs/performans_lab.md)

### 4. Ödev 3.4: Analitik Katman ve Star Schema Tasarımı
* **Kapsam:** OLTP şemadan `fct_orders`, `fct_order_items`, `dim_customer`, `dim_product`, `dim_date` tablolarına geçiş.
* **SCD Type 2 & Idempotent ETL:** `dim_customer` tablosunda `valid_from`, `valid_to` ve `is_current` kolonları ile tarihsel değişim takibi ve tekrar çalıştırıldığında veriyi bozmayan idempotent yükleme scriptleri.
* **Performans Karşılaştırması:** 10 karmaşık analitik sorunun OLTP ve Star Schema üzerindeki milisaniye bazlı kıyaslaması (**3.5 kattan 275 kata varan performans artışı**).
* **Rapor:** [`docs/star_schema_tasarim.md`](docs/star_schema_tasarim.md)

### 5. Ödev 3.5: DuckDB ile Dosya Analitiği
* **Kapsam:** Sunucu kurmadan, büyük Parquet dosyaları üzerinde DuckDB ile yüksek performanslı analitik sorgular çalıştırma ve Pandas ile bellek/süre karşılaştırmaları.
* **Rapor:** [`docs/duckdb_benchmark.md`](docs/duckdb_benchmark.md)

### 6. Ödev 3.6: Araştırma Ödevleri
* **Kapsam:** 
  1. *OLTP vs OLAP:* Satır bazlı (Row-oriented) ve kolon bazlı (Column-oriented) depolama mimarilerinin DuckDB ve PostgreSQL üzerindeki pratik ölçüm ve farkları.
  2. *SCD Type 2 & ML Data Leakage:* Geçmiş tarihli makine öğrenmesi özellikleri (feature) üretirken bugünün müşteri segmentini kullanmanın yarattığı veri sızıntısı (leakage) problemi ve SCD Type 2'nin bu konudaki kritik rolü.
* **Rapor:** [`docs/arastirma_odevleri.md`](docs/arastirma_odevleri.md)

### 7. Ödev 3.7: Kontrol Soruları (Mülakat Soru Bankası)
* **Kapsam:** Veri/AI mülakatlarında en çok elenen kritik SQL kavramlarının incelenmesi:
  * `LEFT JOIN` sonrası `WHERE b.col IS NOT NULL` kullanımı ve `INNER JOIN` farkı.
  * `NOT IN` sorgularında `NULL` değerlerin yarattığı tuzaklar.
  * `COUNT(*)` vs `COUNT(column)` kullanım tehlikeleri.
  * Beklenmeyen satır patlamalarında (fan-out) kontrol edilmesi gereken 3 temel nokta.
  * Window Functions ile `GROUP BY` arasındaki temel mantıksal farklar.
  * Bir tabloya indeks eklemenin sadece getirdiği faydalar değil, sisteme yüklediği yazma maliyetleri (overhead).
* **Rapor:** [`docs/kontrol_sorulari_bolum3.md`](docs/kontrol_sorulari_bolum3.md)

---

## 📊 Özet Performans Karşılaştırma Örneği (OLTP vs Star Schema)

| İş Sorusu | OLTP Süresi | Star Schema Süresi | Başarım Farkı |
| :--- | :--- | :--- | :--- |
| Müşteri Durumuna Göre Toplam Harcama (Query 2) | 1102 ms | 4 ms | **~275 Kat Daha Hızlı** |
| En Değerli İlk 10 Müşteri - LTV (Query 9) | 762 ms | 4 ms | **~190.5 Kat Daha Hızlı** |
| Ürün Bazında İptal/İade Oranları (Query 4) | 394 ms | 4 ms | **~98.5 Kat Daha Hızlı** |

---

## 🛠️ Kurulum ve Çalıştırma

Projeyi yerel ortamınızda ayağa kaldırmak için:

```bash
# Bağımlılıkları yükle ve ortamı hazırla
make install

# Veritabanını kur, migration'ları çalıştır ve tohum (seed) verileri yükle
make seed