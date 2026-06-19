"""
Train and serialise the revenue forecasting model.

Function: train(conn, model_path: str) -> dict
    Orchestrates feature engineering, trains a sklearn Pipeline, and saves
    the bundle to disk with joblib.

Run as __main__ to train interactively:
    python -m src.forecasting.model
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.forecasting.features import build_monthly_aggregates, engineer_features

logger = logging.getLogger("forecasting.model")

FEATURE_COLS = [
    "year",
    "month_sin",
    "month_cos",
    "quarter",
    "category_enc",
    "region_enc",
    "lag_revenue_1",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def train(conn, model_path: str) -> dict:
    """
    Train a LinearRegression pipeline on monthly revenue data and save it.

    Split strategy: chronological — last 20% of rows become the test set.
    This avoids leaking future information into training.

    Parameters
    ----------
    conn:
        Open DuckDB connection that has transactions / products / stores tables.
    model_path:
        File path where the joblib bundle will be written.

    Returns
    -------
    dict with keys: r2_train, r2_test, mae_test, n_train, n_test
    """
    # ------------------------------------------------------------------
    # Build feature matrix
    # ------------------------------------------------------------------
    monthly_df = build_monthly_aggregates(conn)
    if monthly_df.empty:
        raise ValueError("No data returned from build_monthly_aggregates — is the DB populated?")

    feature_df, encoders = engineer_features(monthly_df)

    # Align targets (after engineer_features re-sorts by category/region/year/month)
    # We need monthly_revenue in the same row order as feature_df.
    # engineer_features sorts by category, region, year, month — replicate that sort.
    monthly_sorted = monthly_df.sort_values(
        ["category", "region", "year", "month"]
    ).reset_index(drop=True)
    y = monthly_sorted["monthly_revenue"].values.astype(float)
    X = feature_df[FEATURE_COLS].values

    # ------------------------------------------------------------------
    # Chronological split (no shuffle)
    # ------------------------------------------------------------------
    n_total = len(X)
    split_idx = int(n_total * 0.80)
    # Ensure at least 1 test sample
    split_idx = max(1, min(split_idx, n_total - 1))

    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    # ------------------------------------------------------------------
    # Pipeline: StandardScaler → LinearRegression
    # ------------------------------------------------------------------
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", LinearRegression()),
    ])
    pipeline.fit(X_train, y_train)

    # ------------------------------------------------------------------
    # Evaluate
    # ------------------------------------------------------------------
    r2_train = float(r2_score(y_train, pipeline.predict(X_train)))
    r2_test = float(r2_score(y_test, pipeline.predict(X_test))) if len(y_test) > 1 else float("nan")
    mae_test = float(mean_absolute_error(y_test, pipeline.predict(X_test)))

    metrics = {
        "r2_train": r2_train,
        "r2_test": r2_test,
        "mae_test": mae_test,
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
    }

    logger.info(
        "Training complete — r2_train=%.4f, r2_test=%.4f, mae_test=%.2f, "
        "n_train=%d, n_test=%d",
        r2_train,
        r2_test,
        mae_test,
        len(X_train),
        len(X_test),
    )

    # ------------------------------------------------------------------
    # Persist bundle
    # ------------------------------------------------------------------
    bundle = {
        "model": pipeline,
        "encoders": encoders,
        "feature_cols": FEATURE_COLS,
    }
    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, model_path)
    logger.info("Model bundle saved to %s", model_path)

    return metrics


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import logging as _logging

    _logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    # Local imports here to avoid circular issues when running as script
    import duckdb  # noqa: F401

    from src.config import settings

    logger.info("Connecting to %s", settings.database_path)
    conn = duckdb.connect(settings.database_path)
    try:
        metrics = train(conn, settings.model_path)
        print("\n=== Training Metrics ===")
        for k, v in metrics.items():
            print(f"  {k}: {v}")
    finally:
        conn.close()
