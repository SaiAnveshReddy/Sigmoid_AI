"""
Tests for src.forecasting: features, model training, and prediction.

A self-contained pytest fixture seeds 24 months of synthetic transaction data
(2022–2023) for 2 categories × 2 regions into a temporary DuckDB file.
No conftest fixtures are used for DB setup here.
"""
from __future__ import annotations

import math
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import duckdb
import pandas as pd
import pytest

from src.forecasting.features import build_monthly_aggregates, engineer_features
from src.forecasting.model import train
from src.forecasting.predictor import predict, load_model


# ---------------------------------------------------------------------------
# Fixture: temporary DuckDB with 24 months of synthetic data
# ---------------------------------------------------------------------------

@pytest.fixture()
def seeded_conn(tmp_path):
    """
    In-memory (file-backed) DuckDB with 2 categories × 2 regions × 24 months
    of synthetic monthly transactions.

    Returns an *open* DuckDB connection.  The caller must close it.
    """
    db_path = str(tmp_path / "forecast_test.duckdb")
    conn = duckdb.connect(db_path)

    # -- Schema --
    conn.execute("""
        CREATE TABLE products (
            sku_id       VARCHAR PRIMARY KEY,
            product_name VARCHAR,
            category     VARCHAR,
            brand        VARCHAR,
            package_size VARCHAR,
            list_price   FLOAT,
            launch_date  DATE
        )
    """)
    conn.execute("""
        CREATE TABLE stores (
            store_id   VARCHAR PRIMARY KEY,
            store_name VARCHAR,
            region     VARCHAR,
            state      VARCHAR,
            city       VARCHAR
        )
    """)
    conn.execute("""
        CREATE TABLE transactions (
            transaction_id VARCHAR PRIMARY KEY,
            txn_date       DATE,
            store_id       VARCHAR,
            sku_id         VARCHAR,
            quantity       INTEGER,
            unit_price     FLOAT,
            revenue        FLOAT,
            source         VARCHAR,
            ingested_at    TIMESTAMP
        )
    """)

    # -- Reference data --
    categories = ["Beverages", "Snacks"]
    regions = ["North", "South"]

    for i, cat in enumerate(categories):
        conn.execute(
            "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)",
            [f"SKU{i:03d}", f"{cat} Product", cat, f"Brand{i}", "1kg", 5.0 + i, "2022-01-01"],
        )
    for i, reg in enumerate(regions):
        conn.execute(
            "INSERT INTO stores VALUES (?, ?, ?, ?, ?)",
            [f"STR{i:03d}", f"Store {i}", reg, f"State{i}", f"City{i}"],
        )

    # -- Synthetic transactions: one row per (year, month, category, region) --
    import random
    rng = random.Random(0)  # deterministic
    txn_id = 0
    for month_offset in range(24):
        year = 2022 + month_offset // 12
        month = (month_offset % 12) + 1
        txn_date = f"{year}-{month:02d}-15"
        for cat_i, cat in enumerate(categories):
            for reg_i, reg in enumerate(regions):
                revenue = 8000.0 + rng.uniform(-1000, 1000)
                unit_price = round(revenue / 50, 2)
                txn_id += 1
                conn.execute(
                    """INSERT INTO transactions
                       VALUES (?, ?, ?, ?, ?, ?, ?, 'test', CURRENT_TIMESTAMP)""",
                    [
                        f"TXN{txn_id:05d}",
                        txn_date,
                        f"STR{reg_i:03d}",
                        f"SKU{cat_i:03d}",
                        50,
                        unit_price,
                        round(revenue, 2),
                    ],
                )

    yield conn
    conn.close()


@pytest.fixture()
def trained_model(seeded_conn, tmp_path):
    """Train a model on the seeded DB and return (bundle, model_path)."""
    model_path = str(tmp_path / "test_model.joblib")
    train(seeded_conn, model_path)
    bundle = load_model(model_path)
    return bundle, model_path


# ---------------------------------------------------------------------------
# Feature engineering tests
# ---------------------------------------------------------------------------

class TestBuildMonthlyAggregates:
    def test_returns_dataframe(self, seeded_conn):
        df = build_monthly_aggregates(seeded_conn)
        assert isinstance(df, pd.DataFrame)

    def test_has_more_than_zero_rows(self, seeded_conn):
        df = build_monthly_aggregates(seeded_conn)
        assert len(df) > 0

    def test_expected_columns_present(self, seeded_conn):
        df = build_monthly_aggregates(seeded_conn)
        expected = {"year", "month", "quarter", "category", "region",
                    "monthly_revenue", "txn_count"}
        assert expected.issubset(set(df.columns))

    def test_sorted_by_year_month(self, seeded_conn):
        df = build_monthly_aggregates(seeded_conn)
        pairs = list(zip(df["year"], df["month"]))
        assert pairs == sorted(pairs), "DataFrame should be sorted by year, month"


class TestEngineerFeatures:
    def test_adds_category_enc_column(self, seeded_conn):
        df = build_monthly_aggregates(seeded_conn)
        feature_df, _ = engineer_features(df)
        assert "category_enc" in feature_df.columns

    def test_adds_region_enc_column(self, seeded_conn):
        df = build_monthly_aggregates(seeded_conn)
        feature_df, _ = engineer_features(df)
        assert "region_enc" in feature_df.columns

    def test_adds_month_sin_column(self, seeded_conn):
        df = build_monthly_aggregates(seeded_conn)
        feature_df, _ = engineer_features(df)
        assert "month_sin" in feature_df.columns

    def test_adds_month_cos_column(self, seeded_conn):
        df = build_monthly_aggregates(seeded_conn)
        feature_df, _ = engineer_features(df)
        assert "month_cos" in feature_df.columns

    def test_month_sin_in_valid_range(self, seeded_conn):
        df = build_monthly_aggregates(seeded_conn)
        feature_df, _ = engineer_features(df)
        assert feature_df["month_sin"].between(-1, 1).all(), \
            "month_sin values must be in [−1, 1]"

    def test_month_cos_in_valid_range(self, seeded_conn):
        df = build_monthly_aggregates(seeded_conn)
        feature_df, _ = engineer_features(df)
        assert feature_df["month_cos"].between(-1, 1).all(), \
            "month_cos values must be in [−1, 1]"

    def test_encoders_dict_has_category_key(self, seeded_conn):
        df = build_monthly_aggregates(seeded_conn)
        _, encoders = engineer_features(df)
        assert "category" in encoders

    def test_encoders_dict_has_region_key(self, seeded_conn):
        df = build_monthly_aggregates(seeded_conn)
        _, encoders = engineer_features(df)
        assert "region" in encoders

    def test_lag_revenue_column_present(self, seeded_conn):
        df = build_monthly_aggregates(seeded_conn)
        feature_df, _ = engineer_features(df)
        assert "lag_revenue_1" in feature_df.columns

    def test_lag_revenue_no_nan(self, seeded_conn):
        df = build_monthly_aggregates(seeded_conn)
        feature_df, _ = engineer_features(df)
        assert not feature_df["lag_revenue_1"].isna().any(), \
            "lag_revenue_1 should have no NaN (filled with 0)"


# ---------------------------------------------------------------------------
# Model training tests
# ---------------------------------------------------------------------------

class TestTrain:
    def test_train_returns_metrics_dict(self, seeded_conn, tmp_path):
        model_path = str(tmp_path / "model.joblib")
        metrics = train(seeded_conn, model_path)
        assert isinstance(metrics, dict)

    def test_r2_train_is_float(self, seeded_conn, tmp_path):
        model_path = str(tmp_path / "model.joblib")
        metrics = train(seeded_conn, model_path)
        assert isinstance(metrics["r2_train"], float)

    def test_r2_test_is_float(self, seeded_conn, tmp_path):
        model_path = str(tmp_path / "model.joblib")
        metrics = train(seeded_conn, model_path)
        assert isinstance(metrics["r2_test"], float)

    def test_mae_test_is_non_negative(self, seeded_conn, tmp_path):
        model_path = str(tmp_path / "model.joblib")
        metrics = train(seeded_conn, model_path)
        assert metrics["mae_test"] >= 0

    def test_model_file_created(self, seeded_conn, tmp_path):
        model_path = str(tmp_path / "model.joblib")
        train(seeded_conn, model_path)
        assert Path(model_path).exists()

    def test_n_train_plus_n_test_equals_total(self, seeded_conn, tmp_path):
        df = build_monthly_aggregates(seeded_conn)
        total = len(df)
        model_path = str(tmp_path / "model.joblib")
        metrics = train(seeded_conn, model_path)
        assert metrics["n_train"] + metrics["n_test"] == total


# ---------------------------------------------------------------------------
# Predictor tests
# ---------------------------------------------------------------------------

class TestPredict:
    def test_returns_list_of_correct_length(self, trained_model):
        bundle, _ = trained_model
        results = predict(
            model_bundle=bundle,
            category="Beverages",
            region="North",
            months_ahead=3,
            last_known_date=date(2023, 12, 31),
        )
        assert len(results) == 3

    def test_result_contains_period_key(self, trained_model):
        bundle, _ = trained_model
        results = predict(bundle, "Beverages", "North", 1, date(2023, 12, 31))
        assert "period" in results[0]

    def test_result_contains_predicted_revenue_key(self, trained_model):
        bundle, _ = trained_model
        results = predict(bundle, "Beverages", "North", 1, date(2023, 12, 31))
        assert "predicted_revenue" in results[0]

    def test_period_format_is_yyyy_mm(self, trained_model):
        bundle, _ = trained_model
        results = predict(bundle, "Beverages", "North", 2, date(2023, 11, 30))
        for r in results:
            parts = r["period"].split("-")
            assert len(parts) == 2, f"Expected YYYY-MM but got {r['period']}"
            assert len(parts[0]) == 4
            assert len(parts[1]) == 2

    def test_clips_negative_revenue_to_zero(self, trained_model):
        """
        Mock the sklearn pipeline to return negative predictions and verify
        that predict() clips them to 0.
        """
        bundle, _ = trained_model
        mock_pipeline = MagicMock()
        mock_pipeline.predict.return_value = [-999.0, -1.0, -0.001]

        bundle_copy = dict(bundle)
        bundle_copy["model"] = mock_pipeline

        results = predict(bundle_copy, "Beverages", "North", 3, date(2023, 12, 31))
        for r in results:
            assert r["predicted_revenue"] >= 0.0, \
                f"Negative revenue not clipped: {r['predicted_revenue']}"

    def test_raises_on_unseen_category(self, trained_model):
        bundle, _ = trained_model
        with pytest.raises(ValueError, match="Unknown category"):
            predict(
                bundle,
                category="NonExistentCategory",
                region="North",
                months_ahead=1,
                last_known_date=date(2023, 12, 31),
            )

    def test_raises_on_unseen_region(self, trained_model):
        bundle, _ = trained_model
        with pytest.raises(ValueError, match="Unknown region"):
            predict(
                bundle,
                category="Beverages",
                region="NonExistentRegion",
                months_ahead=1,
                last_known_date=date(2023, 12, 31),
            )

    def test_predictions_advance_correctly_across_year_boundary(self, trained_model):
        """Ensure month/year rollover works (Dec → Jan next year)."""
        bundle, _ = trained_model
        results = predict(bundle, "Beverages", "North", 2, date(2023, 12, 15))
        assert results[0]["period"] == "2024-01"
        assert results[1]["period"] == "2024-02"
