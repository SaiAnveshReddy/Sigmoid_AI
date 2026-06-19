# Shared pytest fixtures.
import pytest
import duckdb
import pandas as pd
import os
from pathlib import Path

@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    """Ensure tests use test config, not production."""
    os.environ.setdefault("GROQ_API_KEY", "")
    os.environ.setdefault("DATABASE_PATH", ":memory:")
    os.environ.setdefault("MODEL_PATH", "models/test_model.joblib")
    os.environ.setdefault("DATA_DIR", "data/raw")
    yield

@pytest.fixture
def temp_db(tmp_path):
    """In-memory DuckDB with schema and seed data for testing."""
    db_path = str(tmp_path / "test.duckdb")
    conn = duckdb.connect(db_path)
    conn.execute("""
        CREATE TABLE products (sku_id VARCHAR PRIMARY KEY, product_name VARCHAR,
            category VARCHAR, brand VARCHAR, package_size VARCHAR, list_price FLOAT, launch_date DATE)
    """)
    conn.execute("""
        CREATE TABLE stores (store_id VARCHAR PRIMARY KEY, store_name VARCHAR,
            region VARCHAR, state VARCHAR, city VARCHAR)
    """)
    conn.execute("""
        CREATE TABLE transactions (transaction_id VARCHAR PRIMARY KEY, txn_date DATE,
            store_id VARCHAR, sku_id VARCHAR, quantity INTEGER, unit_price FLOAT,
            revenue FLOAT, source VARCHAR, ingested_at TIMESTAMP)
    """)
    # Seed minimal data
    categories = ["Beverages", "Snacks", "Dairy"]
    regions = ["North", "South", "East", "West"]
    for i, cat in enumerate(categories):
        conn.execute(f"INSERT INTO products VALUES ('SKU{i:03d}', '{cat} Product', '{cat}', 'Brand{i}', '1L', {2.0+i}, '2022-01-01')")
    for i, region in enumerate(regions):
        conn.execute(f"INSERT INTO stores VALUES ('STR{i:03d}', 'Store {i}', '{region}', 'State{i}', 'City{i}')")
    import random
    random.seed(42)
    for month in range(1, 25):
        year = 2022 + (month - 1) // 12
        m = ((month - 1) % 12) + 1
        for cat_i, cat in enumerate(categories):
            for reg_i, region in enumerate(regions):
                rev = 10000 + random.uniform(-2000, 2000)
                conn.execute("""INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, 'test', CURRENT_TIMESTAMP)""",
                    [f"TXN{month}{cat_i}{reg_i}", f"{year}-{m:02d}-15", f"STR{reg_i:03d}", f"SKU{cat_i:03d}",
                     random.randint(10, 100), round(rev/50, 2), round(rev, 2)])
    conn.close()
    return db_path
