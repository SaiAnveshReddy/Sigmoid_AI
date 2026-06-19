"""Clean raw DataFrames. Each function returns (cleaned_df, quality_report_dict)."""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger("ingestion.cleaner")


def clean_products(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Clean products DataFrame.

    - Drop rows with null sku_id or null category
    - Impute null list_price with median
    - Parse launch_date to datetime.date
    """
    rows_in = len(df)
    out = df.copy()

    # Coerce list_price to numeric before any imputation
    out["list_price"] = pd.to_numeric(out["list_price"], errors="coerce")

    # Drop rows missing required fields
    before_drop = len(out)
    out = out.dropna(subset=["sku_id", "category"])
    nulls_dropped = before_drop - len(out)

    # Impute missing list_price with median of remaining rows
    null_price_mask = out["list_price"].isna()
    price_imputed = int(null_price_mask.sum())
    if price_imputed > 0:
        median_price = out["list_price"].median()
        out.loc[null_price_mask, "list_price"] = median_price
        logger.debug(
            "Imputed %d null list_price values with median %.2f", price_imputed, median_price
        )

    # Parse launch_date
    out["launch_date"] = pd.to_datetime(out["launch_date"], errors="coerce").dt.date

    report = {
        "rows_in": rows_in,
        "rows_out": len(out),
        "nulls_dropped": nulls_dropped,
        "price_imputed": price_imputed,
    }
    logger.info("clean_products: %s", report)
    return out.reset_index(drop=True), report


def clean_stores(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Clean stores DataFrame.

    - Drop rows with null store_id
    - Fill null region with 'Unknown'
    - Deduplicate on store_id (keep first)
    """
    rows_in = len(df)
    out = df.copy()

    # Drop null store_id
    out = out.dropna(subset=["store_id"])

    # Fill null region
    null_region_mask = out["region"].isna()
    region_filled = int(null_region_mask.sum())
    out.loc[null_region_mask, "region"] = "Unknown"

    # Deduplicate on store_id
    before_dedup = len(out)
    out = out.drop_duplicates(subset=["store_id"], keep="first")
    duplicates_removed = before_dedup - len(out)

    report = {
        "rows_in": rows_in,
        "rows_out": len(out),
        "duplicates_removed": duplicates_removed,
        "region_filled": region_filled,
    }
    logger.info("clean_stores: %s", report)
    return out.reset_index(drop=True), report


def _parse_date_mixed(series: pd.Series) -> pd.Series:
    """Parse dates that may be 'YYYY-MM-DD' or 'DD/MM/YYYY'. Returns datetime64 Series."""
    # First pass: standard ISO format
    iso = pd.to_datetime(series, format="%Y-%m-%d", errors="coerce")

    # Second pass: DD/MM/YYYY for values that failed ISO parse
    dmy_mask = iso.isna() & series.notna()
    dmy_parsed = pd.to_datetime(series[dmy_mask], format="%d/%m/%Y", errors="coerce")
    iso = iso.copy()
    iso[dmy_mask] = dmy_parsed

    return iso


def clean_transactions(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Clean transactions DataFrame.

    - Remove duplicate transaction_ids (keep first)
    - Drop rows with null quantity or null store_id
    - Normalize txn_date (YYYY-MM-DD and DD/MM/YYYY); drop unparseable rows
    - Drop rows with unit_price <= 0
    - Recalculate revenue = quantity * unit_price
    - Cast quantity to int, unit_price and revenue to float
    """
    rows_in = len(df)
    out = df.copy()

    # Deduplicate on transaction_id
    before_dedup = len(out)
    out = out.drop_duplicates(subset=["transaction_id"], keep="first")
    duplicates_removed = before_dedup - len(out)

    # Drop null quantity and null store_id
    before_null_drop = len(out)
    out = out.dropna(subset=["quantity", "store_id"])
    nulls_dropped = before_null_drop - len(out)

    # Normalize dates
    before_date = len(out)
    out["txn_date"] = _parse_date_mixed(out["txn_date"])
    out = out.dropna(subset=["txn_date"])
    bad_dates = before_date - len(out)

    # Coerce unit_price to numeric and drop non-positive
    out["unit_price"] = pd.to_numeric(out["unit_price"], errors="coerce")
    before_price = len(out)
    out = out[out["unit_price"] > 0]
    negative_prices = before_price - len(out)

    # Coerce quantity to numeric (needed after NA drop) and cast
    out["quantity"] = pd.to_numeric(out["quantity"], errors="coerce")
    out = out.dropna(subset=["quantity"])
    out["quantity"] = out["quantity"].astype(int)
    out["unit_price"] = out["unit_price"].astype(float)

    # Recalculate revenue
    out["revenue"] = (out["quantity"] * out["unit_price"]).round(2)

    # Convert txn_date to date object (from Timestamp)
    out["txn_date"] = pd.to_datetime(out["txn_date"]).dt.date

    report = {
        "rows_in": rows_in,
        "rows_out": len(out),
        "duplicates_removed": duplicates_removed,
        "nulls_dropped": nulls_dropped,
        "bad_dates": bad_dates,
        "negative_prices": negative_prices,
    }
    logger.info("clean_transactions: %s", report)
    return out.reset_index(drop=True), report
