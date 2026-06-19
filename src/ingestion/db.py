"""DuckDB operations and ingestion pipeline orchestration."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pandas as pd

from src.config import settings
from src.ingestion.cleaner import clean_products, clean_stores, clean_transactions
from src.ingestion.loader import load_products, load_stores, load_transactions

logger = logging.getLogger("ingestion.db")

_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id VARCHAR PRIMARY KEY,
        txn_date DATE NOT NULL,
        store_id VARCHAR NOT NULL,
        sku_id VARCHAR NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price FLOAT NOT NULL,
        revenue FLOAT NOT NULL,
        source VARCHAR DEFAULT 'pos_system',
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS products (
        sku_id VARCHAR PRIMARY KEY,
        product_name VARCHAR,
        category VARCHAR NOT NULL,
        brand VARCHAR,
        package_size VARCHAR,
        list_price FLOAT,
        launch_date DATE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS stores (
        store_id VARCHAR PRIMARY KEY,
        store_name VARCHAR,
        region VARCHAR NOT NULL,
        state VARCHAR,
        city VARCHAR
    )
    """,
]


def get_connection(db_path: str) -> duckdb.DuckDBPyConnection:
    """Open (or create) a DuckDB database file and return the connection."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(db_path)
    logger.debug("Connected to DuckDB at %s", db_path)
    return conn


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create all tables if they do not already exist."""
    for stmt in _SCHEMA_STATEMENTS:
        conn.execute(stmt)
    logger.info("Schema initialised (CREATE TABLE IF NOT EXISTS)")


def upsert_products(conn: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> int:
    """Insert or replace products rows. Returns number of rows written."""
    if df.empty:
        return 0

    cols = ["sku_id", "product_name", "category", "brand", "package_size", "list_price", "launch_date"]
    insert_df = df[[c for c in cols if c in df.columns]].copy()  # noqa: F841 — referenced in SQL

    conn.execute("""
        INSERT INTO products (sku_id, product_name, category, brand, package_size, list_price, launch_date)
        SELECT sku_id, product_name, category, brand, package_size, list_price, launch_date
        FROM insert_df
        ON CONFLICT (sku_id) DO UPDATE SET
            product_name = EXCLUDED.product_name,
            category = EXCLUDED.category,
            brand = EXCLUDED.brand,
            package_size = EXCLUDED.package_size,
            list_price = EXCLUDED.list_price,
            launch_date = EXCLUDED.launch_date
    """)
    rows = len(insert_df)
    logger.info("upsert_products: %d rows written", rows)
    return rows


def upsert_stores(conn: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> int:
    """Insert or replace stores rows. Returns number of rows written."""
    if df.empty:
        return 0

    cols = ["store_id", "store_name", "region", "state", "city"]
    insert_df = df[[c for c in cols if c in df.columns]].copy()  # noqa: F841 — referenced in SQL

    conn.execute("""
        INSERT INTO stores (store_id, store_name, region, state, city)
        SELECT store_id, store_name, region, state, city
        FROM insert_df
        ON CONFLICT (store_id) DO UPDATE SET
            store_name = EXCLUDED.store_name,
            region = EXCLUDED.region,
            state = EXCLUDED.state,
            city = EXCLUDED.city
    """)
    rows = len(insert_df)
    logger.info("upsert_stores: %d rows written", rows)
    return rows


def upsert_transactions(conn: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> int:
    """Insert or replace transaction rows. Returns number of rows written."""
    if df.empty:
        return 0

    cols = ["transaction_id", "txn_date", "store_id", "sku_id", "quantity", "unit_price", "revenue"]
    insert_df = df[[c for c in cols if c in df.columns]].copy()  # noqa: F841 — referenced in SQL

    conn.execute("""
        INSERT INTO transactions (transaction_id, txn_date, store_id, sku_id, quantity, unit_price, revenue)
        SELECT transaction_id, txn_date, store_id, sku_id, quantity, unit_price, revenue
        FROM insert_df
        ON CONFLICT (transaction_id) DO UPDATE SET
            txn_date = EXCLUDED.txn_date,
            store_id = EXCLUDED.store_id,
            sku_id = EXCLUDED.sku_id,
            quantity = EXCLUDED.quantity,
            unit_price = EXCLUDED.unit_price,
            revenue = EXCLUDED.revenue
    """)
    rows = len(insert_df)
    logger.info("upsert_transactions: %d rows written", rows)
    return rows


def run_pipeline(data_dir: str, db_path: str) -> dict:
    """Orchestrate full load -> clean -> upsert pipeline. Returns quality report."""
    logging.basicConfig(level=settings.log_level)

    logger.info("Starting ingestion pipeline: data_dir=%s, db_path=%s", data_dir, db_path)

    # Load
    raw_products = load_products(data_dir)
    raw_stores = load_stores(data_dir)
    raw_transactions = load_transactions(data_dir)

    # Clean
    clean_prod, prod_report = clean_products(raw_products)
    clean_stor, stor_report = clean_stores(raw_stores)
    clean_txn, txn_report = clean_transactions(raw_transactions)

    # Connect & initialise schema
    conn = get_connection(db_path)
    init_schema(conn)

    # Upsert
    prod_written = upsert_products(conn, clean_prod)
    stor_written = upsert_stores(conn, clean_stor)
    txn_written = upsert_transactions(conn, clean_txn)

    conn.close()

    quality_report = {
        "products": {**prod_report, "rows_written": prod_written},
        "stores": {**stor_report, "rows_written": stor_written},
        "transactions": {**txn_report, "rows_written": txn_written},
    }

    logger.info("Pipeline complete. Quality report:")
    for entity, report in quality_report.items():
        logger.info("  %s: %s", entity, report)

    print("\n=== Ingestion Quality Report ===")
    for entity, report in quality_report.items():
        print(f"{entity}:")
        for k, v in report.items():
            print(f"  {k}: {v}")

    return quality_report


if __name__ == "__main__":
    run_pipeline(settings.data_dir, settings.database_path)
