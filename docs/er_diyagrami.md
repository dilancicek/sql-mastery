# 🛒 E-Ticaret OLTP Veritabanı Şeması (Ödev 3.1)

Aşağıdaki diyagram, sistemin temel tablolarını ve ilişkilerini göstermektedir.

```mermaid
erDiagram
    users ||--o{ orders : places
    users ||--o{ reviews : writes
    categories ||--o{ products : contains
    products ||--o{ order_items : includes
    products ||--o{ inventory_movements : tracks
    products ||--o{ reviews : receives
    orders ||--|{ order_items : has
    orders ||--o| payments : generates
    orders ||--o| shipments : requires
    coupons ||--o{ orders : applies_to

    users {
        int id PK
        string name
        string email UK
        string status "CHECK(status IN ('active', 'inactive'))"
        timestamp created_at
    }

    categories {
        int id PK
        string name
        int parent_id FK "Nullable"
    }

    products {
        int id PK
        int category_id FK
        string name
        decimal price "CHECK(price > 0)"
        timestamp created_at
    }

    coupons {
        int id PK
        string code UK
        decimal discount_pct
        timestamp valid_until
    }

    orders {
        int id PK
        int user_id FK
        int coupon_id FK "Nullable"
        decimal total_amount
        string status
        timestamp created_at
    }

    order_items {
        int id PK
        int order_id FK
        int product_id FK
        int quantity "CHECK(quantity > 0)"
        decimal unit_price
    }

    payments {
        int id PK
        int order_id FK
        decimal amount
        string status
        timestamp created_at
    }

    shipments {
        int id PK
        int order_id FK
        string tracking_number
        string status
        timestamp shipped_at
    }

    reviews {
        int id PK
        int user_id FK
        int product_id FK
        int rating "CHECK(rating BETWEEN 1 AND 5)"
        string comment
        timestamp created_at
    }

    inventory_movements {
        int id PK
        int product_id FK
        int quantity
        string movement_type "IN ('in', 'out', 'return')"
        timestamp created_at
    }