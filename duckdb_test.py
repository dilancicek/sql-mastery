import gc
import os
import time
import psutil  # İşletim sistemi seviyesinde gerçek RAM ölçümü için (Windows/Linux uyumlu)

import duckdb
import pandas as pd
import requests

FILE_NAME = "yellow_tripdata_2024-01.parquet"
URL = f"https://d37ci6vzurychx.cloudfront.net/trip-data/{FILE_NAME}"

# 1. VERİ İNDİRME
if not os.path.exists(FILE_NAME):
    print("Veri indiriliyor...")
    with open(FILE_NAME, 'wb') as f:
        f.write(requests.get(URL).content)

print("🔥 DUCKDB VS PANDAS: SÜRE VE BELLEK KAPIŞMASI (GÜNCELLENDİ) 🔥\n")

def get_peak_memory_mb():
    """İşletim sisteminin gördüğü en yüksek (peak) bellek tüketimini döndürür."""
    # Windows için peak_wset, Linux için rss
    mem_info = psutil.Process(os.getpid()).memory_info()
    peak_mem = getattr(mem_info, 'peak_wset', mem_info.rss) 
    return peak_mem / (1024 * 1024)

# --- 2. DUCKDB TESTİ (10 Sorgu Ayrı Ayrı ve Fetchall ile) ---
print("🦆 DuckDB Calisiyor (Disk üzerinden)...")
gc.collect() 
start_time = time.time()

# Sorgular ayrıldı ve SARGable formata uygun hale getirildi
duckdb_queries = [
    f"SELECT passenger_count, AVG(tip_amount) FROM '{FILE_NAME}' GROUP BY passenger_count;",
    f"SELECT CAST(tpep_pickup_datetime AS DATE), COUNT(*) FROM '{FILE_NAME}' GROUP BY 1;",
    f"SELECT payment_type, COUNT(*) FROM '{FILE_NAME}' GROUP BY payment_type;",
    f"SELECT EXTRACT(HOUR FROM tpep_pickup_datetime), COUNT(*) FROM '{FILE_NAME}' GROUP BY 1;",
    f"SELECT round(trip_distance), AVG(total_amount) FROM '{FILE_NAME}' WHERE trip_distance < 20 GROUP BY 1;",
    f"SELECT VendorID, COUNT(*) FROM '{FILE_NAME}' GROUP BY VendorID;",
    f"SELECT COUNT(*) FROM '{FILE_NAME}' WHERE passenger_count = 0 AND total_amount > 50;",
    f"SELECT AVG(total_amount) FROM '{FILE_NAME}' WHERE RatecodeID = 2;",
    f"SELECT (COUNT(CASE WHEN tip_amount = 0 THEN 1 END) * 100.0 / COUNT(*)) FROM '{FILE_NAME}';",
    f"SELECT MAX(trip_distance), MIN(total_amount) FROM '{FILE_NAME}';"
]

# Her sorgu tek tek çalıştırılıp veriler fetchall() ile belleğe çekiliyor
for q in duckdb_queries:
    duckdb.execute(q).fetchall()

duck_time = time.time() - start_time
duck_mem_mb = get_peak_memory_mb()

print(f"✅ Süre:   {duck_time:.4f} sn")
print(f"✅ Zirve Bellek: {duck_mem_mb:.2f} MB\n")

# --- 3. PANDAS TESTİ ---
print("🐢 Pandas Calisiyor (Tamamini RAM'e alarak)...")
gc.collect()
start_time = time.time()

# Pandas aynı işi yapmak için tüm dosyayı RAM'e yüklemek ZORUNDADIR
df = pd.read_parquet(FILE_NAME)
df.groupby('passenger_count')['tip_amount'].mean()
df.groupby(df['tpep_pickup_datetime'].dt.date).size()
df.groupby('payment_type').size()
df.groupby(df['tpep_pickup_datetime'].dt.hour).size()
df[df['trip_distance'] < 20].copy().groupby(df['trip_distance'].round())['total_amount'].mean()
df.groupby('VendorID').size()
len(df[(df['passenger_count'] == 0) & (df['total_amount'] > 50)])
df[df['RatecodeID'] == 2]['total_amount'].mean()
(len(df[df['tip_amount'] == 0]) * 100.0) / len(df)
df['trip_distance'].max(), df['total_amount'].min()

pandas_time = time.time() - start_time
pandas_mem_mb = get_peak_memory_mb()

print(f"❌ Süre:   {pandas_time:.4f} sn")
print(f"❌ Zirve Bellek: {pandas_mem_mb:.2f} MB\n")

# --- SONUÇ ---
print("="*50)
print(f"HIZ FARK: DuckDB {pandas_time / duck_time:.1f}x daha hizli.")
print(f"RAM FARK: Pandas {pandas_mem_mb / duck_mem_mb:.1f}x daha fazla RAM tüketti.")
print("="*50)