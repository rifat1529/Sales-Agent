import random
import sqlite3
from pathlib import Path
from .config import DB_PATH

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    customer_name TEXT NOT NULL,
    city TEXT NOT NULL,
    segment TEXT NOT NULL,
    signup_date TEXT NOT NULL
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_price REAL NOT NULL CHECK(unit_price >= 0)
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(order_id),
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    unit_price REAL NOT NULL CHECK(unit_price >= 0),
    discount_pct REAL NOT NULL CHECK(discount_pct BETWEEN 0 AND 100)
);

CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_items_order ON order_items(order_id);
CREATE INDEX idx_items_product ON order_items(product_id);
"""

def build_database(db_path=DB_PATH, seed=20261115):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    rng = random.Random(seed)
    con = sqlite3.connect(db_path)
    try:
        con.executescript(SCHEMA_SQL)
        cities = ["Dhaka", "Chattogram", "Sylhet", "Rajshahi", "Khulna", "Rangpur"]
        segments = ["Consumer", "Corporate", "Small Business"]
        for cid in range(1, 121):
            con.execute(
                "INSERT INTO customers VALUES (?, ?, ?, ?, ?)",
                (cid, f"Customer {cid:03d}", rng.choice(cities),
                 rng.choice(segments), f"2024-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}")
            )

        catalog = [
            ("Laptop Air", "Electronics", 850.0), ("Monitor 24", "Electronics", 190.0),
            ("Wireless Mouse", "Electronics", 25.0), ("Keyboard Pro", "Electronics", 65.0),
            ("Office Chair", "Furniture", 220.0), ("Standing Desk", "Furniture", 410.0),
            ("Desk Lamp", "Furniture", 38.0), ("Notebook Pack", "Stationery", 12.0),
            ("Pen Set", "Stationery", 8.0), ("Printer Paper", "Stationery", 18.0),
            ("Coffee Maker", "Appliances", 95.0), ("Air Purifier", "Appliances", 175.0),
            ("Water Bottle", "Lifestyle", 20.0), ("Backpack", "Lifestyle", 55.0),
            ("Headphones", "Electronics", 120.0), ("Webcam", "Electronics", 75.0),
            ("Bookshelf", "Furniture", 160.0), ("Whiteboard", "Stationery", 45.0),
            ("Toaster", "Appliances", 42.0), ("Fitness Band", "Lifestyle", 89.0),
            ("USB Hub", "Electronics", 32.0), ("Floor Mat", "Furniture", 29.0),
            ("Marker Set", "Stationery", 14.0), ("Blender", "Appliances", 68.0),
            ("Travel Mug", "Lifestyle", 24.0), ("Router", "Electronics", 110.0),
            ("Filing Cabinet", "Furniture", 245.0), ("Sticky Notes", "Stationery", 6.0),
            ("Rice Cooker", "Appliances", 72.0), ("Yoga Mat", "Lifestyle", 34.0),
        ]
        for pid, (name, category, price) in enumerate(catalog, 1):
            con.execute("INSERT INTO products VALUES (?, ?, ?, ?)", (pid, name, category, price))

        statuses = ["completed", "completed", "completed", "shipped", "cancelled", "processing"]
        order_id, item_id = 1, 1
        for _ in range(500):
            customer_id = rng.randint(1, 120)
            month = rng.randint(1, 12)
            day = rng.randint(1, 28)
            con.execute(
                "INSERT INTO orders VALUES (?, ?, ?, ?)",
                (order_id, customer_id, f"2025-{month:02d}-{day:02d}", rng.choice(statuses))
            )
            for _ in range(rng.randint(1, 4)):
                product_id = rng.randint(1, len(catalog))
                base_price = catalog[product_id - 1][2]
                quantity = rng.randint(1, 5)
                discount = rng.choice([0.0, 5.0, 10.0, 15.0, 20.0])
                con.execute(
                    "INSERT INTO order_items VALUES (?, ?, ?, ?, ?, ?)",
                    (item_id, order_id, product_id, quantity, base_price, discount)
                )
                item_id += 1
            order_id += 1
        con.commit()
    finally:
        con.close()
    return {"customers": 120, "products": 30, "orders": 500, "order_items": item_id - 1}

if __name__ == "__main__":
    print("Created database:", DB_PATH)
    print("Rows:", build_database())
