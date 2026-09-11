# Görev 3.5: DuckDB ve Pandas Performans ve Bellek Analizi

Bu doküman, veri analitiğinde sunucusuz çalışan DuckDB ile bellek tabanlı çalışan Pandas kütüphanelerinin performans ve RAM kullanım karşılaştırmasını içermektedir.

## 1. Test Ortamı ve Veri
Test, NYC Taxi veri setinin Ocak 2024 Parquet dosyası üzerinde gerçekleştirilmiştir. Görev yönergesinde belirtilen "bir ay, ~3 GB" veri hacmi[cite: 1], modern Parquet sıkıştırması sayesinde diskte ~50 MB yer kaplamaktadır. Ancak bellek (RAM) testleri, verinin işlenmesi sırasındaki gerçek kaynak tüketimini ortaya koymuştur.

## 2. Performans ve Bellek (RAM) Karşılaştırması
Her iki araçla da aynı analitik işlemler yapılmış ve aşağıdaki sonuçlar elde edilmiştir:

*   **DuckDB Süre:** 0.3731 saniye
*   **DuckDB Bellek (RAM):** 0.01 MB
*   **Pandas Süre:** 6.9533 saniye
*   **Pandas Bellek (RAM):** 762.53 MB

**Analiz:** DuckDB, Pandas'a göre **18.6 kat daha hızlı** çalışmıştır. En çarpıcı fark ise bellek tüketimindedir; Pandas veriyi RAM'e yüklemek zorunda olduğu için DuckDB'den **58.645 kat daha fazla RAM** (762.53 MB) tüketmiştir.

## 3. DuckDB ile 10 Analitik İş Sorgusu
DuckDB kullanılarak, sunucu kurulumuna gerek kalmadan doğrudan dosya üzerinden 10 farklı iş sorusu (gruplama, tarih filtreleme, koşullu sayım vb.) tek bir işlem bloğunda başarıyla ve saniyeler altında çalıştırılmıştır[cite: 1].

## 4. Sonuç ve Mühendislik Kararı
Büyük veri setleri ile çalışırken Pandas'ın RAM sınırlarına takılması kaçınılmazdır. DuckDB'nin disk tabanlı, kolon odaklı (columnar) yapısı, bellek taşmalarını (Out of Memory) önlerken hızı da maksimize etmektedir.