"""SQLite schema, connection helpers, and read-only query functions."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

from src.config import DB_PATH

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS stores (
    store_id TEXT PRIMARY KEY,
    store_name TEXT NOT NULL,
    location TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    reorder_level INTEGER NOT NULL,
    target_stock INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sales (
    sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_date TEXT NOT NULL,
    store_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    revenue REAL NOT NULL,
    FOREIGN KEY (store_id) REFERENCES stores(store_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS inventory (
    inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    current_stock INTEGER NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (store_id) REFERENCES stores(store_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    UNIQUE (store_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(sale_date);
CREATE INDEX IF NOT EXISTS idx_sales_store ON sales(store_id);
CREATE INDEX IF NOT EXISTS idx_sales_product ON sales(product_id);
CREATE INDEX IF NOT EXISTS idx_sales_store_product_date ON sales(store_id, product_id, sale_date);
CREATE INDEX IF NOT EXISTS idx_inventory_lookup ON inventory(store_id, product_id);
"""


def connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = Path(db_path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_connection(db_path: Optional[Path] = None) -> Iterator[sqlite3.Connection]:
    conn = connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


def initialize_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def database_ready(db_path: Optional[Path] = None) -> bool:
    path = Path(db_path or DB_PATH)
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        with get_connection(path) as conn:
            stores = conn.execute("SELECT COUNT(*) AS n FROM stores").fetchone()["n"]
            products = conn.execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"]
            sales = conn.execute("SELECT COUNT(*) AS n FROM sales").fetchone()["n"]
            return stores > 0 and products > 0 and sales > 0
    except sqlite3.Error as exc:
        logger.error("Database readiness check failed: %s", exc)
        return False


def fetch_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]


def fetch_one(sql: str, params: tuple[Any, ...] = ()) -> Optional[dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


def list_stores() -> list[dict[str, Any]]:
    return fetch_all(
        "SELECT store_id, store_name, location FROM stores ORDER BY store_id"
    )


def get_store(store_id: str) -> Optional[dict[str, Any]]:
    return fetch_one(
        "SELECT store_id, store_name, location FROM stores WHERE store_id = ?",
        (store_id,),
    )


def list_products() -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT product_id, product_name, category, price, reorder_level, target_stock
        FROM products
        ORDER BY product_id
        """
    )


def get_product(product_id: str) -> Optional[dict[str, Any]]:
    return fetch_one(
        """
        SELECT product_id, product_name, category, price, reorder_level, target_stock
        FROM products
        WHERE product_id = ?
        """,
        (product_id,),
    )


def find_products_by_name(name: str) -> list[dict[str, Any]]:
    needle = f"%{name.strip()}%"
    return fetch_all(
        """
        SELECT product_id, product_name, category, price, reorder_level, target_stock
        FROM products
        WHERE lower(product_name) LIKE lower(?)
        ORDER BY product_id
        """,
        (needle,),
    )


def find_stores_by_name_or_location(text: str) -> list[dict[str, Any]]:
    needle = f"%{text.strip()}%"
    return fetch_all(
        """
        SELECT store_id, store_name, location
        FROM stores
        WHERE lower(store_name) LIKE lower(?)
           OR lower(location) LIKE lower(?)
        ORDER BY store_id
        """,
        (needle, needle),
    )


def get_sales(
    product_id: Optional[str] = None,
    store_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> list[dict[str, Any]]:
    clauses = ["1=1"]
    params: list[Any] = []
    if product_id:
        clauses.append("product_id = ?")
        params.append(product_id)
    if store_id:
        clauses.append("store_id = ?")
        params.append(store_id)
    if start_date:
        clauses.append("sale_date >= ?")
        params.append(start_date)
    if end_date:
        clauses.append("sale_date <= ?")
        params.append(end_date)
    sql = f"""
        SELECT sale_id, sale_date, store_id, product_id, quantity, revenue
        FROM sales
        WHERE {' AND '.join(clauses)}
        ORDER BY sale_date, sale_id
    """
    return fetch_all(sql, tuple(params))


def get_sales_aggregates(
    product_id: Optional[str] = None,
    store_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict[str, Any]:
    clauses = ["1=1"]
    params: list[Any] = []
    if product_id:
        clauses.append("product_id = ?")
        params.append(product_id)
    if store_id:
        clauses.append("store_id = ?")
        params.append(store_id)
    if start_date:
        clauses.append("sale_date >= ?")
        params.append(start_date)
    if end_date:
        clauses.append("sale_date <= ?")
        params.append(end_date)
    sql = f"""
        SELECT
            COALESCE(SUM(quantity), 0) AS units,
            COALESCE(SUM(revenue), 0) AS revenue,
            COUNT(*) AS row_count
        FROM sales
        WHERE {' AND '.join(clauses)}
    """
    row = fetch_one(sql, tuple(params)) or {"units": 0, "revenue": 0, "row_count": 0}
    return {
        "units": int(row["units"] or 0),
        "revenue": float(row["revenue"] or 0),
        "row_count": int(row["row_count"] or 0),
    }


def get_daily_sales(
    product_id: Optional[str] = None,
    store_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> list[dict[str, Any]]:
    clauses = ["1=1"]
    params: list[Any] = []
    if product_id:
        clauses.append("product_id = ?")
        params.append(product_id)
    if store_id:
        clauses.append("store_id = ?")
        params.append(store_id)
    if start_date:
        clauses.append("sale_date >= ?")
        params.append(start_date)
    if end_date:
        clauses.append("sale_date <= ?")
        params.append(end_date)
    sql = f"""
        SELECT sale_date,
               SUM(quantity) AS units,
               SUM(revenue) AS revenue
        FROM sales
        WHERE {' AND '.join(clauses)}
        GROUP BY sale_date
        ORDER BY sale_date
    """
    rows = fetch_all(sql, tuple(params))
    return [
        {
            "sale_date": r["sale_date"],
            "units": int(r["units"] or 0),
            "revenue": float(r["revenue"] or 0),
        }
        for r in rows
    ]


def get_inventory(
    product_id: Optional[str] = None,
    store_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    clauses = ["1=1"]
    params: list[Any] = []
    if product_id:
        clauses.append("i.product_id = ?")
        params.append(product_id)
    if store_id:
        clauses.append("i.store_id = ?")
        params.append(store_id)
    sql = f"""
        SELECT
            i.inventory_id,
            i.store_id,
            s.store_name,
            s.location,
            i.product_id,
            p.product_name,
            p.category,
            p.price,
            p.reorder_level,
            p.target_stock,
            i.current_stock,
            i.updated_at
        FROM inventory i
        JOIN stores s ON s.store_id = i.store_id
        JOIN products p ON p.product_id = i.product_id
        WHERE {' AND '.join(clauses)}
        ORDER BY i.store_id, i.product_id
    """
    return fetch_all(sql, tuple(params))


def sales_velocity_map(start_date: str, end_date: str) -> dict[tuple[str, str], dict[str, Any]]:
    rows = fetch_all(
        """
        SELECT store_id, product_id,
               COALESCE(SUM(quantity), 0) AS units,
               COALESCE(SUM(revenue), 0) AS revenue
        FROM sales
        WHERE sale_date >= ? AND sale_date <= ?
        GROUP BY store_id, product_id
        """,
        (start_date, end_date),
    )
    return {
        (r["store_id"], r["product_id"]): {
            "units": int(r["units"] or 0),
            "revenue": float(r["revenue"] or 0),
        }
        for r in rows
    }


def product_sales_velocity_map(start_date: str, end_date: str) -> dict[str, dict[str, Any]]:
    rows = fetch_all(
        """
        SELECT product_id,
               COALESCE(SUM(quantity), 0) AS units,
               COALESCE(SUM(revenue), 0) AS revenue
        FROM sales
        WHERE sale_date >= ? AND sale_date <= ?
        GROUP BY product_id
        """,
        (start_date, end_date),
    )
    return {
        r["product_id"]: {"units": int(r["units"] or 0), "revenue": float(r["revenue"] or 0)}
        for r in rows
    }


def date_bounds() -> dict[str, Optional[str]]:
    row = fetch_one("SELECT MIN(sale_date) AS min_date, MAX(sale_date) AS max_date FROM sales")
    if not row:
        return {"min_date": None, "max_date": None}
    return {"min_date": row["min_date"], "max_date": row["max_date"]}
