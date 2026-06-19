"""
Feature engineering for the revenue forecasting model.

Functions
---------
build_monthly_aggregates(conn) -> pd.DataFrame
    Query transactions, join stores + products, aggregate to monthly level.

engineer_features(df) -> tuple[pd.DataFrame, dict]
    Label-encode categoricals, add sin/cos seasonality and lag features.
"""
from __future__ import annotations

import logging
import math

import pandas as pd
from sklearn.preprocessing import LabelEncoder

logger = logging.getLogger("forecasting.features")


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def build_monthly_aggregates(conn) -> pd.DataFrame:
    """
    Query transactions joined with stores and products, aggregate to monthly
    level per (category, region).

    Returns a DataFrame with columns:
        year, month, quarter, category, region, monthly_revenue, txn_count
    sorted by year, month.
    """
    sql = """
        SELECT
            YEAR(t.txn_date)                          AS year,
            MONTH(t.txn_date)                         AS month,
            CAST(CEIL(MONTH(t.txn_date) / 3.0) AS INTEGER) AS quarter,
            p.category                                AS category,
            s.region                                  AS region,
            SUM(t.revenue)                            AS monthly_revenue,
            COUNT(t.transaction_id)                   AS txn_count
        FROM transactions t
        JOIN products  p ON t.sku_id   = p.sku_id
        JOIN stores    s ON t.store_id = s.store_id
        GROUP BY
            YEAR(t.txn_date),
            MONTH(t.txn_date),
            p.category,
            s.region
        ORDER BY year, month
    """
    df = conn.execute(sql).df()

    # Ensure correct dtypes
    for col in ("year", "month", "quarter", "txn_count"):
        df[col] = df[col].astype(int)
    df["monthly_revenue"] = df["monthly_revenue"].astype(float)
    df["category"] = df["category"].astype(str)
    df["region"] = df["region"].astype(str)

    logger.info(
        "build_monthly_aggregates: returned %d rows spanning %s months",
        len(df),
        df[["year", "month"]].drop_duplicates().shape[0],
    )
    return df


def engineer_features(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Transform raw monthly aggregates into a model-ready feature matrix.

    Steps
    -----
    1. Label-encode ``category`` and ``region``.
    2. Add sin/cos month encoding to capture seasonality.
    3. Add ``lag_revenue_1``: previous-month revenue for the same
       (category, region) group; NaN values filled with 0.

    Parameters
    ----------
    df:
        Output of :func:`build_monthly_aggregates`.

    Returns
    -------
    feature_df:
        DataFrame with columns:
        [year, month_sin, month_cos, quarter,
         category_enc, region_enc, lag_revenue_1]
    encoders_dict:
        {"category": LabelEncoder, "region": LabelEncoder}
    """
    df = df.copy()

    # ------------------------------------------------------------------
    # 1. Label encode categoricals
    # ------------------------------------------------------------------
    cat_enc = LabelEncoder()
    reg_enc = LabelEncoder()
    df["category_enc"] = cat_enc.fit_transform(df["category"])
    df["region_enc"] = reg_enc.fit_transform(df["region"])

    encoders = {"category": cat_enc, "region": reg_enc}

    # ------------------------------------------------------------------
    # 2. Cyclical month encoding
    # ------------------------------------------------------------------
    df["month_sin"] = df["month"].apply(lambda m: math.sin(2 * math.pi * m / 12))
    df["month_cos"] = df["month"].apply(lambda m: math.cos(2 * math.pi * m / 12))

    # ------------------------------------------------------------------
    # 3. Lag revenue (same category + region, previous calendar month)
    #    Sort by (category, region, year, month), shift(1) within group.
    # ------------------------------------------------------------------
    df = df.sort_values(["category", "region", "year", "month"]).reset_index(drop=True)
    df["lag_revenue_1"] = (
        df.groupby(["category", "region"])["monthly_revenue"]
        .shift(1)
        .fillna(0.0)
    )

    feature_cols = [
        "year",
        "month_sin",
        "month_cos",
        "quarter",
        "category_enc",
        "region_enc",
        "lag_revenue_1",
    ]
    feature_df = df[feature_cols].copy()

    logger.info(
        "engineer_features: produced feature matrix with shape %s",
        feature_df.shape,
    )
    return feature_df, encoders
