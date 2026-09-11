import duckdb
import pandas as pd
import time
import tracemalloc
import gc
import os
import requests

FILE_NAME = "yellow_tripdata_2024-01.parquet"
URL = f"https://d37ci6vzurychx.cloudfront.net/trip-data/{FILE_NAME}"

# 1. VERİ İNDİRME (Eğer yoksa 1 aylık veriyi indirir)
if not os.path.exists(FILE_NAME):
    print("Veri indiriliyor...")
    with open(FILE_NAME, 'wb') as f:
        f.write(requests.get(URL).content)

print("🔥 DUCKDB VS PANDAS: SÜRE VE BELLEK KAPIŞMASI 🔥\n")

# --- 2. DUCKDB TESTİ (10 Sorgu) ---
print("🦆 DuckDB Çalışıyor (Disk üzerinden)...")
gc.collect() 
tracemalloc.start() # Bellek ölçümünü başlat
start_time = time.time()

# PDF'te istenen 10 analitik sorgu
duckdb.execute(f"""
    SELECT passenger_count, AVG(tip_amount) FROM '{FILE_NAME}' GROUP BY passenger_count;
    SELECT CAST(tpep_pickup_datetime AS DATE), COUNT(*) FROM '{FILE_NAME}' GROUP BY 1;
    SELECT payment_type, COUNT(*) FROM '{FILE_NAME}' GROUP BY payment_type;
    SELECT EXTRACT(HOUR FROM tpep_pickup_datetime), COUNT(*) FROM '{FILE_NAME}' GROUP BY 1;
    SELECT round(trip_distance), AVG(total_amount) FROM '{FILE_NAME}' WHERE trip_distance < 20 GROUP BY 1;
    SELECT VendorID, COUNT(*) FROM '{FILE_NAME}' GROUP BY VendorID;
    SELECT COUNT(*) FROM '{FILE_NAME}' WHERE passenger_count = 0 AND total_amount > 50;
    SELECT AVG(total_amount) FROM '{FILE_NAME}' WHERE RatecodeID = 2;
    SELECT (COUNT(CASE WHEN tip_amount = 0 THEN 1 END) * 100.0 / COUNT(*)) FROM '{FILE_NAME}';
    SELECT MAX(trip_distance), MIN(total_amount) FROM '{FILE_NAME}';
""")

duck_time = time.time() - start_time
_, duck_peak = tracemalloc.get_traced_memory()
tracemalloc.stop()

duck_mem_mb = duck_peak / (1024 * 1024)
print(f"✅ Süre:   {duck_time:.4f} sn")
print(f"✅ Bellek: {duck_mem_mb:.2f} MB\n")

# --- 3. PANDAS TESTİ ---
print("🐢 Pandas Çalışıyor (Tamamını RAM'e alarak)...")
gc.collect()
tracemalloc.start()
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
_, pandas_peak = tracemalloc.get_traced_memory()
tracemalloc.stop()

pandas_mem_mb = pandas_peak / (1024 * 1024)
print(f"❌ Süre:   {pandas_time:.4f} sn")
print(f"❌ Bellek: {pandas_mem_mb:.2f} MB\n")

# --- SONUÇ ---
print("="*50)
print(f"HIZ FARK: DuckDB {pandas_time / duck_time:.1f}x daha hızlı.")
print(f"RAM FARK: Pandas {pandas_mem_mb / duck_mem_mb:.1f}x daha fazla RAM tüketti.")
print("="*50)