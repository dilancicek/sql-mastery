# DuckDB vs Pandas Performans Analizi

Bu testte 1 aylik NYC Yellow Taxi verisi (yaklasik 3 milyon satir) uzerinde 10 farkli analitik is sorgusu calistirilmistir.

## 1. Donanim ve Olcum Kriterleri
* RAM olcumleri isletim sistemi seviyesinde (psutil/peak_wset) yapilmistir.
* DuckDB veriyi diskten okuyup islerken, Pandas tum veriyi RAM'e alarak islemistir.
* Adil kiyaslama icin DuckDB sorgulari ayri ayri calistirilmis ve sonuclar fetchall() ile bellege cekilmistir.

## 2. Genel Performans Sonuclari
* **DuckDB:** Sure: 0.59 sn | Zirve RAM: 113.86 MB
* **Pandas:** Sure: 4.27 sn | Zirve RAM: 1374.74 MB
* **Sonuc:** DuckDB 7.2x daha hizli calismis ve Pandas 12.1x daha fazla RAM tuketmistir.

## 3. Analitik Sorgular ve Is Yorumlari (Bulgular)

| # | Sorgu Amaci | Is Yorumu (Bulgu) |
|---|---|---|
| 1 | Yolcu sayisina gore ortalama bahsis | Yolcu sayisi arttikca bahsis miktarinda dogrusal bir artis gozlemlenmemistir. |
| 2 | Gunluk toplam yolculuk sayisi | Hafta sonlari ve tatil gunlerinde yolculuk taleplerinde belirgin dalgalanmalar vardir. |
| 3 | Odeme tipine gore islem sayisi | Kredi karti kullanimi nakit odemeye gore acik ara onde olup ana odeme yontemidir. |
| 4 | Saatlik talep yogunlugu | Sabah is giris ve aksam is cikis saatlerinde (rush hour) talep zirve yapmaktadir. |
| 5 | Kisa mesafelerde ortalama ucret | 20 mil altindaki yolculuklarda mesafe ile ucret korelasyonu yuksektir. |
| 6 | Saglayici (Vendor) pazar payi | Pazardaki iki ana saglayicidan birinin islem hacmi digerine gore daha fazladir. |
| 7 | Yolcusuz ama yuksek ucretli kayitlar | Sifir yolcu gorunmesine ragmen 50$ uzeri ucret kesilen anomali (hatali) kayitlar tespit edilmistir. |
| 8 | JFK Havalimani ortalama ucreti | Havalimani (RatecodeID=2) tarifesinde sabit ucret politikasinin uygulandigi dogrulanmistir. |
| 9 | Sifir bahsis oraninin tespiti | Nakit odemelerde bahsis sisteme girilmedigi icin sifir bahsis orani suni olarak yuksek cikmaktadir. |
| 10 | Max mesafe ve min ucret kontrolu | Veri setinde eksi (negatif) ucretli iade kayitlari ve asiri yuksek mesafeli outlier'lar bulunmaktadir. |