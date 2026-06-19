"""Load raw CSVs from data directory. No cleaning — raw DataFrames only."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger("ingestion.loader")


def _load_csv(data_dir: str, filename: str) -> pd.DataFrame:
    path = Path(data_dir) / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Expected CSV not found: {path}. "
            f"Run scripts/generate_data.py to create synthetic data."
        )
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    # Replace empty strings with NaN for consistent downstream handling
    df = df.replace("", pd.NA)
    logger.debug("Loaded %s: %d rows, columns=%s", filename, len(df), list(df.columns))
    return df


def load_products(data_dir: str) -> pd.DataFrame:
    """Load products CSV. Returns raw DataFrame with all columns as strings."""
    return _load_csv(data_dir, "products.csv")


def load_stores(data_dir: str) -> pd.DataFrame:
    """Load stores CSV. Returns raw DataFrame with all columns as strings."""
    return _load_csv(data_dir, "stores.csv")


def load_transactions(data_dir: str) -> pd.DataFrame:
    """Load transactions CSV. Returns raw DataFrame with all columns as strings."""
    return _load_csv(data_dir, "transactions.csv")
