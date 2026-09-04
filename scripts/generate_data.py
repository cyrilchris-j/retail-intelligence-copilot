"""Generate a seeded synthetic retail dataset and load it into SQLite."""

from __future__ import annotations

import csv
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import BUSINESS_DATE, DATA_DIR, DB_PATH  # noqa: E402
from src.database import connect, initialize_schema  # noqa: E402

SEED = 42
HISTORY_DAYS = 90

STORES = [
    {"store_id": "S01", "store_name": "Chennai Central", "location": "Chennai"},
    {"store_id": "S02", "store_name": "Coimbatore", "location": "Coimbatore"},
    {"store_id": "S03", "store_name": "Bengaluru MG Road", "location": "Bengaluru"},
    {"store_id": "S04", "store_name": "Hyderabad Banjara", "location": "Hyderabad"},
    {"store_id": "S05", "store_name": "Madurai", "location": "Madurai"},
]

# Seeded catalogue. Scenario notes are encoded in generate_sales / generate_inventory.
PRODUCTS = [
    {"product_id": "P001", "product_name": "LED Desk Lamp", "category": "Electronics", "price": 899.0, "reorder_level": 40, "target_stock": 80, "base_daily": 3.2},
    {"product_id": "P002", "product_name": "Bluetooth Speaker", "category": "Electronics", "price": 1499.0, "reorder_level": 25, "target_stock": 50, "base_daily": 2.1},
    {"product_id": "P003", "product_name": "Power Bank 10000mAh", "category": "Electronics", "price": 1299.0, "reorder_level": 35, "target_stock": 70, "base_daily": 2.8},
    {"product_id": "P004", "product_name": "HDMI Cable 2m", "category": "Electronics", "price": 249.0, "reorder_level": 50, "target_stock": 100, "base_daily": 4.0},
    {"product_id": "P005", "product_name": "USB-C Charging Cable", "category": "Electronics", "price": 199.0, "reorder_level": 60, "target_stock": 120, "base_daily": 5.5},
    {"product_id": "P006", "product_name": "Wireless Mouse", "category": "Electronics", "price": 799.0, "reorder_level": 30, "target_stock": 60, "base_daily": 6.8},
    {"product_id": "P007", "product_name": "Wireless Mouse Pro", "category": "Electronics", "price": 1299.0, "reorder_level": 20, "target_stock": 40, "base_daily": 1.6},
    {"product_id": "P008", "product_name": "Wireless Mouse Mini", "category": "Electronics", "price": 699.0, "reorder_level": 20, "target_stock": 40, "base_daily": 1.4},
    {"product_id": "P009", "product_name": "Mechanical Keyboard", "category": "Electronics", "price": 2499.0, "reorder_level": 18, "target_stock": 36, "base_daily": 1.8},
    {"product_id": "P010", "product_name": "Membrane Keyboard", "category": "Electronics", "price": 899.0, "reorder_level": 25, "target_stock": 50, "base_daily": 2.2},
    {"product_id": "P011", "product_name": "USB-C Hub", "category": "Electronics", "price": 1599.0, "reorder_level": 22, "target_stock": 44, "base_daily": 2.4},
    {"product_id": "P012", "product_name": "Webcam HD", "category": "Electronics", "price": 1899.0, "reorder_level": 15, "target_stock": 30, "base_daily": 1.3},
    {"product_id": "P013", "product_name": "Noise Cancelling Headphones", "category": "Electronics", "price": 3999.0, "reorder_level": 12, "target_stock": 24, "base_daily": 0.9},
    {"product_id": "P014", "product_name": "Wired Earphones", "category": "Electronics", "price": 299.0, "reorder_level": 40, "target_stock": 80, "base_daily": 3.6},
    {"product_id": "P015", "product_name": "Portable SSD 1TB", "category": "Electronics", "price": 5499.0, "reorder_level": 10, "target_stock": 20, "base_daily": 0.7},
    {"product_id": "P016", "product_name": "Office Chair", "category": "Office", "price": 7499.0, "reorder_level": 8, "target_stock": 16, "base_daily": 0.35},
    {"product_id": "P017", "product_name": "Ergonomic Chair", "category": "Office", "price": 11999.0, "reorder_level": 6, "target_stock": 12, "base_daily": 0.25},
    {"product_id": "P018", "product_name": "Standing Desk Converter", "category": "Office", "price": 8999.0, "reorder_level": 6, "target_stock": 12, "base_daily": 0.3},
    {"product_id": "P019", "product_name": "Desk Organizer", "category": "Office", "price": 499.0, "reorder_level": 30, "target_stock": 60, "base_daily": 2.0},
    {"product_id": "P020", "product_name": "A4 Copier Paper Ream", "category": "Office", "price": 349.0, "reorder_level": 40, "target_stock": 80, "base_daily": 3.1},
    {"product_id": "P021", "product_name": "Ballpoint Pen Pack", "category": "Office", "price": 99.0, "reorder_level": 80, "target_stock": 160, "base_daily": 6.0},
    {"product_id": "P022", "product_name": "Stapler Heavy Duty", "category": "Office", "price": 399.0, "reorder_level": 20, "target_stock": 40, "base_daily": 1.1},
    {"product_id": "P023", "product_name": "Whiteboard Marker Set", "category": "Office", "price": 249.0, "reorder_level": 25, "target_stock": 50, "base_daily": 1.7},
    {"product_id": "P024", "product_name": "Electric Kettle", "category": "Home", "price": 1299.0, "reorder_level": 18, "target_stock": 36, "base_daily": 1.5},
    {"product_id": "P025", "product_name": "Water Bottle 1L", "category": "Home", "price": 349.0, "reorder_level": 40, "target_stock": 80, "base_daily": 3.4},
    {"product_id": "P026", "product_name": "Storage Box Large", "category": "Home", "price": 799.0, "reorder_level": 15, "target_stock": 30, "base_daily": 0.4},
    {"product_id": "P027", "product_name": "Table Clock", "category": "Home", "price": 599.0, "reorder_level": 18, "target_stock": 36, "base_daily": 1.0},
    {"product_id": "P028", "product_name": "LED Night Light", "category": "Home", "price": 299.0, "reorder_level": 25, "target_stock": 50, "base_daily": 1.8},
    {"product_id": "P029", "product_name": "Phone Case Clear", "category": "Accessories", "price": 249.0, "reorder_level": 50, "target_stock": 100, "base_daily": 4.4},
    {"product_id": "P030", "product_name": "Screen Protector Pack", "category": "Accessories", "price": 199.0, "reorder_level": 50, "target_stock": 100, "base_daily": 4.1},
    {"product_id": "P031", "product_name": "Laptop Sleeve 15", "category": "Accessories", "price": 699.0, "reorder_level": 20, "target_stock": 40, "base_daily": 1.4},
    {"product_id": "P032", "product_name": "Mouse Pad XL", "category": "Accessories", "price": 349.0, "reorder_level": 30, "target_stock": 60, "base_daily": 2.3},
    {"product_id": "P033", "product_name": "Cable Organizer Kit", "category": "Accessories", "price": 199.0, "reorder_level": 25, "target_stock": 50, "base_daily": 1.6},
    {"product_id": "P034", "product_name": "Notebook A5", "category": "Stationery", "price": 79.0, "reorder_level": 60, "target_stock": 120, "base_daily": 5.0},
    {"product_id": "P035", "product_name": "Sticky Notes Pack", "category": "Stationery", "price": 59.0, "reorder_level": 50, "target_stock": 100, "base_daily": 3.8},
    {"product_id": "P036", "product_name": "Highlighter Set", "category": "Stationery", "price": 129.0, "reorder_level": 30, "target_stock": 60, "base_daily": 2.0},
    {"product_id": "P037", "product_name": "File Folder Pack", "category": "Stationery", "price": 149.0, "reorder_level": 35, "target_stock": 70, "base_daily": 2.5},
    {"product_id": "P038", "product_name": "Calculator Basic", "category": "Stationery", "price": 249.0, "reorder_level": 20, "target_stock": 40, "base_daily": 1.2},
    {"product_id": "P039", "product_name": "Gift Card Envelope", "category": "Stationery", "price": 29.0, "reorder_level": 40, "target_stock": 80, "base_daily": 1.0},
    {"product_id": "P040", "product_name": "Extension Cord 5m", "category": "Home", "price": 449.0, "reorder_level": 20, "target_stock": 40, "base_daily": 1.3},
]

STORE_MULTIPLIER = {
    "S01": 1.15,
    "S02": 1.00,
    "S03": 1.20,
    "S04": 0.95,
    "S05": 0.52,  # underperforming store
}

WEEKDAY_FACTOR = [0.75, 0.95, 1.00, 1.05, 1.15, 1.35, 1.20]


def daterange(end: date, days: int) -> list[date]:
    start = end - timedelta(days=days - 1)
    return [start + timedelta(days=i) for i in range(days)]


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def generate_sales(rng: np.random.Generator, end: date) -> list[dict]:
    days = daterange(end, HISTORY_DAYS)
    products = {p["product_id"]: p for p in PRODUCTS}
    rows: list[dict] = []
    sale_id = 1

    for day in days:
        days_from_end = (end - day).days
        weekday = day.weekday()
        for store in STORES:
            for product in PRODUCTS:
                pid = product["product_id"]
                mean = product["base_daily"] * STORE_MULTIPLIER[store["store_id"]]
                mean *= WEEKDAY_FACTOR[weekday]

                # Mild seasonal drift: slight growth for accessories, slight decline for chairs.
                if pid in {"P029", "P030"}:
                    mean *= 1.0 + 0.002 * (HISTORY_DAYS - days_from_end)
                if pid in {"P016", "P026"}:
                    mean *= max(0.25, 1.0 - 0.006 * (HISTORY_DAYS - days_from_end))

                # Mechanical Keyboard spike in the last 14 days.
                if pid == "P009" and days_from_end < 14:
                    mean *= 1.75
                # USB-C Hub drop in the last 14 days.
                if pid == "P011" and days_from_end < 14:
                    mean *= 0.58
                # Wireless Mouse remains fast-moving, slight recent decline at Chennai.
                if pid == "P006" and store["store_id"] == "S01" and days_from_end < 14:
                    mean *= 0.88
                # Noise-cancelling headphones spike at Bengaluru recently.
                if pid == "P013" and store["store_id"] == "S03" and days_from_end < 14:
                    mean *= 1.9
                # Office Chair decline is strongest at Coimbatore.
                if pid == "P016" and store["store_id"] == "S02" and days_from_end < 21:
                    mean *= 0.55

                qty = int(rng.poisson(max(mean, 0.05)))
                if qty <= 0:
                    continue
                revenue = round(qty * product["price"], 2)
                rows.append(
                    {
                        "sale_id": sale_id,
                        "sale_date": day.isoformat(),
                        "store_id": store["store_id"],
                        "product_id": pid,
                        "quantity": qty,
                        "revenue": revenue,
                    }
                )
                sale_id += 1
                _ = products
    return rows


def generate_inventory(rng: np.random.Generator, as_of: date) -> list[dict]:
    """Set current stock to encode stock-out, healthy, and overstock scenarios."""
    rows: list[dict] = []
    inventory_id = 1
    updated_at = datetime.combine(as_of, datetime.min.time()).isoformat()

    overrides = {
        # Low stock + high velocity (demo stock-out).
        ("S01", "P006"): 18,
        ("S03", "P006"): 12,
        ("S01", "P005"): 22,
        ("S04", "P021"): 16,
        # Overstock + slow / declining sales.
        ("S02", "P016"): 86,
        ("S01", "P016"): 54,
        ("S02", "P026"): 92,
        ("S05", "P017"): 41,
        # Healthy coverage.
        ("S01", "P001"): 72,
        ("S03", "P004"): 110,
        ("S02", "P034"): 140,
        # Keyboard spike: stock still adequate but watch.
        ("S03", "P009"): 28,
        ("S01", "P009"): 22,
        # USB-C Hub drop: inventory not critical, demand is.
        ("S01", "P011"): 48,
        ("S02", "P011"): 41,
        # Competing attention: Portable SSD healthy stock, headphones low at Bengaluru.
        ("S03", "P013"): 6,
        ("S04", "P015"): 19,
    }

    for store in STORES:
        for product in PRODUCTS:
            key = (store["store_id"], product["product_id"])
            if key in overrides:
                stock = overrides[key]
            else:
                target = product["target_stock"]
                noise = int(rng.normal(0, max(3, target * 0.12)))
                stock = max(0, int(target * STORE_MULTIPLIER[store["store_id"]] + noise))
            rows.append(
                {
                    "inventory_id": inventory_id,
                    "store_id": store["store_id"],
                    "product_id": product["product_id"],
                    "current_stock": stock,
                    "updated_at": updated_at,
                }
            )
            inventory_id += 1
    return rows


def load_sqlite(stores: list[dict], products: list[dict], sales: list[dict], inventory: list[dict]) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = connect(DB_PATH)
    try:
        initialize_schema(conn)
        conn.executemany(
            "INSERT INTO stores (store_id, store_name, location) VALUES (:store_id, :store_name, :location)",
            stores,
        )
        conn.executemany(
            """
            INSERT INTO products (product_id, product_name, category, price, reorder_level, target_stock)
            VALUES (:product_id, :product_name, :category, :price, :reorder_level, :target_stock)
            """,
            [
                {k: p[k] for k in ("product_id", "product_name", "category", "price", "reorder_level", "target_stock")}
                for p in products
            ],
        )
        conn.executemany(
            """
            INSERT INTO sales (sale_id, sale_date, store_id, product_id, quantity, revenue)
            VALUES (:sale_id, :sale_date, :store_id, :product_id, :quantity, :revenue)
            """,
            sales,
        )
        conn.executemany(
            """
            INSERT INTO inventory (inventory_id, store_id, product_id, current_stock, updated_at)
            VALUES (:inventory_id, :store_id, :product_id, :current_stock, :updated_at)
            """,
            inventory,
        )
        conn.commit()
        counts = {
            "stores": conn.execute("SELECT COUNT(*) FROM stores").fetchone()[0],
            "products": conn.execute("SELECT COUNT(*) FROM products").fetchone()[0],
            "sales": conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0],
            "inventory": conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0],
        }
        print(f"Loaded SQLite {DB_PATH}: {counts}")
    finally:
        conn.close()


def main() -> None:
    rng = np.random.default_rng(SEED)
    end = date.fromisoformat(BUSINESS_DATE)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    store_rows = list(STORES)
    product_rows = [
        {k: p[k] for k in ("product_id", "product_name", "category", "price", "reorder_level", "target_stock")}
        for p in PRODUCTS
    ]
    sales_rows = generate_sales(rng, end)
    inventory_rows = generate_inventory(rng, end)

    write_csv(DATA_DIR / "stores.csv", store_rows, ["store_id", "store_name", "location"])
    write_csv(
        DATA_DIR / "products.csv",
        product_rows,
        ["product_id", "product_name", "category", "price", "reorder_level", "target_stock"],
    )
    write_csv(
        DATA_DIR / "sales.csv",
        sales_rows,
        ["sale_id", "sale_date", "store_id", "product_id", "quantity", "revenue"],
    )
    write_csv(
        DATA_DIR / "inventory.csv",
        inventory_rows,
        ["inventory_id", "store_id", "product_id", "current_stock", "updated_at"],
    )

    load_sqlite(store_rows, product_rows, sales_rows, inventory_rows)
    sales_df = pd.DataFrame(sales_rows)
    print(
        "Sales span {min} to {max}; {n} rows; units={units}".format(
            min=sales_df["sale_date"].min(),
            max=sales_df["sale_date"].max(),
            n=len(sales_df),
            units=int(sales_df["quantity"].sum()),
        )
    )


if __name__ == "__main__":
    main()
