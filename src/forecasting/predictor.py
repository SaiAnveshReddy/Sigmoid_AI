"""
Load the trained model bundle and run revenue inference.

Functions
---------
load_model(model_path) -> dict
predict(model_bundle, category, region, months_ahead, last_known_date) -> list[dict]
get_available_categories(model_bundle) -> list[str]
get_available_regions(model_bundle) -> list[str]
"""
from __future__ import annotations

import logging
import math
from datetime import date, timedelta
from typing import Any

import joblib
import numpy as np

logger = logging.getLogger("forecasting.predictor")


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def load_model(model_path: str) -> dict:
    """
    Load a joblib bundle written by :func:`src.forecasting.model.train`.

    Returns the dict: {model, encoders, feature_cols}

    Raises
    ------
    FileNotFoundError
        If model_path does not exist on disk.
    """
    bundle: dict = joblib.load(model_path)
    logger.info("Loaded model bundle from %s", model_path)
    return bundle


def predict(
    model_bundle: dict,
    category: str,
    region: str,
    months_ahead: int,
    last_known_date: date,
) -> list[dict]:
    """
    Generate revenue predictions for future periods.

    Parameters
    ----------
    model_bundle:
        Dict returned by :func:`load_model`.
    category:
        Product category string (must exist in encoder classes).
    region:
        Store region string (must exist in encoder classes).
    months_ahead:
        Number of future months to predict (1–12).
    last_known_date:
        The latest date present in the training data; predictions start
        the month after this date.

    Returns
    -------
    list of dicts: [{"period": "2025-01", "predicted_revenue": 12345.67}, ...]
    Predicted revenues are clipped to 0 (non-negative).

    Raises
    ------
    ValueError
        If category or region is not seen in the training encoder.
    """
    pipeline = model_bundle["model"]
    encoders: dict = model_bundle["encoders"]
    feature_cols: list[str] = model_bundle["feature_cols"]

    # ------------------------------------------------------------------
    # Validate category / region against encoder classes
    # ------------------------------------------------------------------
    cat_enc = encoders["category"]
    reg_enc = encoders["region"]

    if category not in cat_enc.classes_:
        available = ", ".join(sorted(cat_enc.classes_))
        raise ValueError(
            f"Unknown category '{category}'. "
            f"Available categories: {available}"
        )
    if region not in reg_enc.classes_:
        available = ", ".join(sorted(reg_enc.classes_))
        raise ValueError(
            f"Unknown region '{region}'. "
            f"Available regions: {available}"
        )

    category_enc = int(cat_enc.transform([category])[0])
    region_enc = int(reg_enc.transform([region])[0])

    # ------------------------------------------------------------------
    # Build future periods
    # ------------------------------------------------------------------
    rows = []
    # Start from the month *after* last_known_date
    cursor_year = last_known_date.year
    cursor_month = last_known_date.month

    # We track a rolling "last_revenue" for the lag feature.
    # Bootstrap with 0 — we have no previous revenue for future months.
    lag_revenue = 0.0

    for _ in range(months_ahead):
        # Advance by one month
        cursor_month += 1
        if cursor_month > 12:
            cursor_month = 1
            cursor_year += 1

        quarter = math.ceil(cursor_month / 3)
        month_sin = math.sin(2 * math.pi * cursor_month / 12)
        month_cos = math.cos(2 * math.pi * cursor_month / 12)

        row = {
            "year": cursor_year,
            "month_sin": month_sin,
            "month_cos": month_cos,
            "quarter": quarter,
            "category_enc": category_enc,
            "region_enc": region_enc,
            "lag_revenue_1": lag_revenue,
        }
        rows.append(row)

    # Build feature matrix in the correct column order
    import pandas as pd  # local import to keep module-level imports light
    feat_df = pd.DataFrame(rows)[feature_cols]
    X = feat_df.values

    raw_preds: np.ndarray = pipeline.predict(X)

    results = []
    cursor_year = last_known_date.year
    cursor_month = last_known_date.month

    for i, raw_val in enumerate(raw_preds):
        cursor_month += 1
        if cursor_month > 12:
            cursor_month = 1
            cursor_year += 1

        predicted_revenue = float(max(0.0, raw_val))
        period = f"{cursor_year:04d}-{cursor_month:02d}"
        results.append({"period": period, "predicted_revenue": predicted_revenue})

    logger.info(
        "predict: generated %d predictions for category=%s, region=%s",
        len(results),
        category,
        region,
    )
    return results


def get_available_categories(model_bundle: dict) -> list[str]:
    """Return all category labels known to the trained encoder."""
    return list(model_bundle["encoders"]["category"].classes_)


def get_available_regions(model_bundle: dict) -> list[str]:
    """Return all region labels known to the trained encoder."""
    return list(model_bundle["encoders"]["region"].classes_)
