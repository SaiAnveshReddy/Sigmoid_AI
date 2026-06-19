"""Pytest tests for the CPG sales ingestion pipeline."""

from __future__ import annotations

import datetime
from pathlib import Path

import pandas as pd
import pytest

from src.ingestion.cleaner import clean_products, clean_stores, clean_transactions
from src.ingestion.db import get_connection, run_pipeline
from src.ingestion.loader import load_transactions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_txn_df(**overrides) -> pd.DataFrame:
    """Return a minimal valid transactions DataFrame (all strings, like the CSV loader produces)."""
    base = {
        "transaction_id": ["TXN0000001", "TXN0000002", "TXN0000003"],
        "txn_date": ["2023-06-01", "2023-07-15", "2023-08-20"],
        "store_id": ["STR001", "STR002", "STR003"],
        "sku_id": ["SKU0001", "SKU0002", "SKU0003"],
        "quantity": ["5", "3", "10"],
        "unit_price": ["2.50", "5.00", "1.25"],
        "revenue": ["12.50", "15.00", "12.50"],
    }
    base.update(overrides)
    return pd.DataFrame(base)


# ---------------------------------------------------------------------------
# Loader tests
# ---------------------------------------------------------------------------


def test_load_transactions_returns_dataframe(tmp_path):
    """load_transactions returns a DataFrame with required columns."""
    import scripts.generate_data as gen  # noqa: PLC0415

    # Point generator output to tmp_path so we don't pollute data/raw
    original_out_dir = gen.OUT_DIR
    gen.OUT_DIR = tmp_path
    try:
        gen.main()
    finally:
        gen.OUT_DIR = original_out_dir

    df = load_transactions(str(tmp_path))
    required_cols = {
        "transaction_id",
        "txn_date",
        "store_id",
        "sku_id",
        "quantity",
        "unit_price",
        "revenue",
    }
    assert required_cols.issubset(set(df.columns))
    assert len(df) > 0


# ---------------------------------------------------------------------------
# Cleaner: transactions
# ---------------------------------------------------------------------------


def test_clean_transactions_removes_duplicates():
    """Duplicate transaction_ids are removed; only first occurrence kept."""
    df = _make_txn_df(
        transaction_id=["TXN0000001", "TXN0000001", "TXN0000002"],
        txn_date=["2023-06-01", "2023-06-01", "2023-07-01"],
        store_id=["STR001", "STR001", "STR002"],
        sku_id=["SKU0001", "SKU0001", "SKU0002"],
        quantity=["5", "5", "3"],
        unit_price=["2.50", "2.50", "5.00"],
        revenue=["12.50", "12.50", "15.00"],
    )
    cleaned, report = clean_transactions(df)
    assert report["duplicates_removed"] == 1
    assert len(cleaned) == 2
    assert cleaned["transaction_id"].nunique() == 2


def test_clean_transactions_handles_date_formats():
    """Both YYYY-MM-DD and DD/MM/YYYY date strings are parsed correctly."""
    df = _make_txn_df(
        transaction_id=["TXN0000001", "TXN0000002", "TXN0000003"],
        txn_date=["2023-06-01", "15/07/2023", "2023-08-20"],
    )
    cleaned, report = clean_transactions(df)
    assert report["bad_dates"] == 0
    assert len(cleaned) == 3
    # All dates should be date objects (not strings)
    for d in cleaned["txn_date"]:
        assert isinstance(d, datetime.date), f"Expected datetime.date, got {type(d)}: {d}"


def test_clean_transactions_drops_negative_prices():
    """Rows with unit_price <= 0 are removed."""
    df = _make_txn_df(
        transaction_id=["TXN0000001", "TXN0000002", "TXN0000003"],
        unit_price=["2.50", "-1.00", "0.00"],
    )
    cleaned, report = clean_transactions(df)
    assert report["negative_prices"] == 2
    assert len(cleaned) == 1
    assert all(cleaned["unit_price"] > 0)


def test_clean_transactions_drops_null_quantity():
    """Rows with null quantity are removed."""
    df = _make_txn_df(
        transaction_id=["TXN0000001", "TXN0000002", "TXN0000003"],
        quantity=["5", None, "3"],
    )
    cleaned, report = clean_transactions(df)
    assert report["nulls_dropped"] >= 1
    assert len(cleaned) == 2
    assert cleaned["quantity"].notna().all()


# ---------------------------------------------------------------------------
# Cleaner: products
# ---------------------------------------------------------------------------


def test_clean_products_imputes_missing_price():
    """Null list_price rows are imputed with the median price."""
    df = pd.DataFrame(
        {
            "sku_id": ["SKU0001", "SKU0002", "SKU0003", "SKU0004"],
            "product_name": ["A", "B", "C", "D"],
            "category": ["Beverages", "Snacks", "Dairy", "Beverages"],
            "brand": ["BrandA", "BrandB", "BrandC", "BrandA"],
            "package_size": ["500ml", "200g", "1L", "330ml"],
            "list_price": ["4.00", "6.00", None, "8.00"],
            "launch_date": ["2020-01-01", "2019-06-15", "2021-03-10", "2018-11-20"],
        }
    )
    cleaned, report = clean_products(df)
    assert report["price_imputed"] == 1
    # Median of [4.0, 6.0, 8.0] = 6.0
    imputed_row = cleaned[cleaned["sku_id"] == "SKU0003"]
    assert not imputed_row.empty
    assert abs(float(imputed_row["list_price"].iloc[0]) - 6.0) < 0.01


# ---------------------------------------------------------------------------
# Pipeline integration test
# ---------------------------------------------------------------------------


def test_run_pipeline_creates_tables(tmp_path):
    """run_pipeline loads, cleans, and writes all 3 tables to a temp DuckDB."""
    import scripts.generate_data as gen  # noqa: PLC0415

    # Generate data into tmp_path/raw/
    data_dir = tmp_path / "raw"
    data_dir.mkdir()
    original_out_dir = gen.OUT_DIR
    gen.OUT_DIR = data_dir
    try:
        gen.main()
    finally:
        gen.OUT_DIR = original_out_dir

    db_path = str(tmp_path / "test.duckdb")
    report = run_pipeline(str(data_dir), db_path)

    conn = get_connection(db_path)
    for table in ("products", "stores", "transactions"):
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert count > 0, f"Expected rows in {table}, got 0"

    conn.close()

    assert report["products"]["rows_written"] > 0
    assert report["stores"]["rows_written"] > 0
    assert report["transactions"]["rows_written"] > 0
