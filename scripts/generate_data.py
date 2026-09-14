import csv
import os
import random
from datetime import datetime

import numpy as np
from faker import Faker

# Türkçe veriler için Faker'ı ayarlayalım
fake = Faker('tr_TR')
os.makedirs('data', exist_ok=True)

# Hedef satır sayıları (Toplamda ~500k satırı bulacak)
NUM_USERS = 50000
NUM_PRODUCTS = 1000
NUM_ORDERS = 150000
NUM_CATEGORIES = 20

print("🚀 Sentetik veri üretimi başlıyor... Lütfen bekleyin.")

# 1. KULLANICILAR (USERS) - %5 Eksik Veri (NULL) Senaryosu
print("Kullanıcılar üretiliyor...")
with open('data/users.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['id', 'name', 'email', 'status', 'created_at'])
    for i in range(1, NUM_USERS + 1):
        # %5 ihtimalle status null olsun (Eksik veri anomalisi)
        status = 'active' if random.random() > 0.1 else 'inactive'
        status = '' if random.random() < 0.05 else status 
        created_at = fake.date_time_between(start_date='-3y', end_date='now')
        writer.writerow([i, fake.name(), fake.unique.email(), status, created_at])

# 2. ÜRÜNLER VE KATEGORİLER
print("Kategoriler ve Ürünler üretiliyor...")
with open('data/categories.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['id', 'name', 'parent_id'])
    for i in range(1, NUM_CATEGORIES + 1):
        parent_id = random.randint(1, 5) if i > 5 else ''
        writer.writerow([i, fake.word().capitalize(), parent_id])

with open('data/products.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['id', 'category_id', 'name', 'price', 'created_at'])
    for i in range(1, NUM_PRODUCTS + 1):
        price = round(random.uniform(10.0, 5000.0), 2)
        # Kasti Anomali: Birkaç ürünün fiyatı çok uçuk olsun
        if i % 100 == 0: price = round(random.uniform(50000.0, 100000.0), 2) 
        writer.writerow([i, random.randint(1, NUM_CATEGORIES), fake.catch_phrase(), price, fake.date_time_between(start_date='-3y')])

# 3. SİPARİŞLER VE İADELER - Mevsimsellik ve %2 İade
print("Siparişler üretiliyor (Mevsimsellik simülasyonu ile)...")
orders = []
with open('data/orders.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['id', 'user_id', 'coupon_id', 'total_amount', 'status', 'created_at'])
    
    for i in range(1, NUM_ORDERS + 1):
        # Mevsimsellik: Kasım (Black Friday) ve Aralık aylarında daha çok sipariş tarihi üret
        if random.random() < 0.3:
            month = random.choice([11, 12])
            year = random.choice([2024, 2025])
            created_at = fake.date_time_between_dates(datetime(year, month, 1), datetime(year, month, 28))  # noqa: DTZ001
        else:
            created_at = fake.date_time_between(start_date='-2y', end_date='now')

        # %2 iade (return) oranı
        status_chance = random.random()
        if status_chance < 0.02:
            status = 'returned'
        elif status_chance < 0.05:
            status = 'cancelled'
        else:
            status = 'completed'

        user_id = random.randint(1, NUM_USERS)
        writer.writerow([i, user_id, '', 0, status, created_at])
        orders.append(i)

# 4. SİPARİŞ DETAYLARI - Güç Yasası (Power Law)
print("Sipariş detayları üretiliyor (Pareto - Güç Yasası ile)...")
# Numpy kullanarak ürün ID'lerini Zipf (power law) dağılımıyla seçiyoruz (az sayıda ürün çok satar)
product_ids = np.random.zipf(a=1.5, size=NUM_ORDERS * 2)
product_ids = np.clip(product_ids, 1, NUM_PRODUCTS) # Sınırları aşanları törpüle

with open('data/order_items.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['id', 'order_id', 'product_id', 'quantity', 'unit_price'])
    
    item_id = 1
    for order_id in orders:
        num_items = random.randint(1, 4) # Bir siparişte 1-4 arası ürün
        for _ in range(num_items):
            prod_id = int(random.choice(product_ids))
            qty = random.randint(1, 3)
            writer.writerow([item_id, order_id, prod_id, qty, round(random.uniform(10.0, 500.0), 2)])
            item_id += 1

print("🎉 İşlem Tamamlandı! Tüm CSV dosyaları 'data' klasörüne kaydedildi. Toplam satır sayısı ~500.000'i aştı.")