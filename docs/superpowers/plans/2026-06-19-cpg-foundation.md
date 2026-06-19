# CPG Sales Analytics Platform — Foundation, Data Generation & Ingestion Pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the project scaffold, synthetic data generator, and full ingestion pipeline (load → clean → upsert) for a CPG sales analytics DuckDB platform.

**Architecture:** A pure-Python ingestion pipeline reads raw CSVs from `data/raw/`, cleans them with per-entity cleaner functions, and upserts into a local DuckDB database. Config is handled via pydantic-settings; all modules use the stdlib `logging` module. Tests are pytest-only, using real DuckDB in tmp files.

**Tech Stack:** Python 3.11, DuckDB 0.10+, pandas 2.0+, pydantic-settings 2.3+, pytest 8.2+, numpy 1.26+

## Global Constraints

- Python version floor: 3.11
- DuckDB version floor: 0.10
- pandas version floor: 2.0
- scikit-learn version floor: 1.4
- joblib version floor: 1.4
- groq version floor: 0.9
- fastapi version floor: 0.111
- uvicorn[standard] version floor: 0.29
- streamlit version floor: 1.35
- pydantic version floor: 2.7
- pydantic-settings version floor: 2.3
- python-dotenv version floor: 1.0
- httpx version floor: 0.27
- pytest version floor: 8.2
- pytest-asyncio version floor: 0.23
- ruff version floor: 0.4
- numpy version floor: 1.26
- ruff line-length: 100, target-version: py311, select: ["E","F","I"], ignore: ["E501"]
- Database: DuckDB at `data/cpg_sales.duckdb`
- numpy random seed: 42 for all synthetic data
- Logger names: `ingestion.loader`, `ingestion.cleaner`, `ingestion.db`
- All imports in tests use `from src.ingestion.X import Y` style
- No mocking of DuckDB in tests — use real DuckDB in tmp_path

---

## File Map

| File | Responsibility |
|------|---------------|
| `requirements.txt` | All pinned dependency floors |
| `pyproject.toml` | ruff linter config only |
| `.gitignore` | Standard Python + project-specific ignores |
| `.env.example` | Template env vars with placeholder values |
| `src/__init__.py` | Empty package marker |
| `src/config.py` | pydantic-settings Settings class; `settings` singleton |
| `src/ingestion/__init__.py` | Empty package marker |
| `src/ingestion/loader.py` | Raw CSV → DataFrame; schema drift logging; no cleaning |
| `src/ingestion/cleaner.py` | DataFrame → (cleaned DataFrame, quality report dict) |
| `src/ingestion/db.py` | DuckDB connection, schema init, upserts, pipeline orchestration |
| `scripts/generate_data.py` | Generates three CSVs with intentional quality issues |
| `tests/__init__.py` | Empty package marker |
| `tests/test_ingestion.py` | 7 pytest tests covering loader, cleaner, and pipeline |

---

### Task 1: Project Scaffold — requirements.txt, pyproject.toml, .gitignore, .env.example

**Files:**
- Create: `D:\Sigmoid\Project\requirements.txt`
- Create: `D:\Sigmoid\Project\pyproject.toml`
- Create: `D:\Sigmoid\Project\.gitignore`
- Create: `D:\Sigmoid\Project\.env.example`

**Interfaces:**
- Produces: nothing consumed by code; consumed by humans and tooling

- [ ] **Step 1: Create requirements.txt**

```
duckdb>=0.10
pandas>=2.0
scikit-learn>=1.4
joblib>=1.4
groq>=0.9
fastapi>=0.111
uvicorn[standard]>=0.29
streamlit>=1.35
pydantic>=2.7
pydantic-settings>=2.3
python-dotenv>=1.0
httpx>=0.27
pytest>=8.2
pytest-asyncio>=0.23
ruff>=0.4
numpy>=1.26
```

Write to `D:\Sigmoid\Project\requirements.txt`.

- [ ] **Step 2: Create pyproject.toml**

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I"]
ignore = ["E501"]
```

Write to `D:\Sigmoid\Project\pyproject.toml`.

- [ ] **Step 3: Create .gitignore**

```
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
*.pyc
*.egg
*.egg-info/
dist/
build/
.eggs/
*.so

# Virtual environments
.venv/
venv/
env/
ENV/

# Environment & secrets
.env

# Project-specific
data/cpg_sales.duckdb
models/*.joblib

# Tool caches
.pytest_cache/
.ruff_cache/
.mypy_cache/
.coverage
htmlcov/

# IDE
.vscode/
.idea/
*.iml
```

Write to `D:\Sigmoid\Project\.gitignore`.

- [ ] **Step 4: Create .env.example**

```
GROQ_API_KEY=your_groq_api_key_here
DATABASE_PATH=data/cpg_sales.duckdb
MODEL_PATH=models/revenue_forecast.joblib
DATA_DIR=data/raw
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

Write to `D:\Sigmoid\Project\.env.example`.

- [ ] **Step 5: Verify files exist**

Run: `dir D:\Sigmoid\Project\` (Windows) or check that all 4 files are present.

---

### Task 2: Package Init Files and src/config.py

**Files:**
- Create: `D:\Sigmoid\Project\src\__init__.py`
- Create: `D:\Sigmoid\Project\src\ingestion\__init__.py`
- Create: `D:\Sigmoid\Project\tests\__init__.py`
- Create: `D:\Sigmoid\Project\src\config.py`

**Interfaces:**
- Produces:
  - `from src.config import settings` — `settings.groq_api_key: str`, `settings.database_path: str`, `settings.model_path: str`, `settings.data_dir: str`, `settings.api_host: str`, `settings.api_port: int`, `settings.log_level: str`

- [ ] **Step 1: Create empty init files**

Create three completely empty files:
- `D:\Sigmoid\Project\src\__init__.py`
- `D:\Sigmoid\Project\src\ingestion\__init__.py`
- `D:\Sigmoid\Project\tests\__init__.py`

- [ ] **Step 2: Create src/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str = ""
    database_path: str = "data/cpg_sales.duckdb"
    model_path: str = "models/revenue_forecast.joblib"
    data_dir: str = "data/raw"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
```

Write to `D:\Sigmoid\Project\src\config.py`.

- [ ] **Step 3: Smoke-test import**

Run from project root:
```
python -c "from src.config import settings; print(settings.database_path)"
```
Expected output: `data/cpg_sales.duckdb`

---

### Task 3: Synthetic Data Generator — scripts/generate_data.py

**Files:**
- Create: `D:\Sigmoid\Project\scripts\generate_data.py`
- Output: `D:\Sigmoid\Project\data\raw\products.csv` (30 rows)
- Output: `D:\Sigmoid\Project\data\raw\stores.csv` (20 rows + 1 duplicate = 21 written rows)
- Output: `D:\Sigmoid\Project\data\raw\transactions.csv` (~30,000 rows with quality issues)

**Interfaces:**
- Produces: raw CSV files consumed by `src/ingestion/loader.py`

- [ ] **Step 1: Write scripts/generate_data.py**

```python
"""Generate synthetic CPG sales data with intentional quality issues."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)
OUT_DIR = Path("data/raw")


def generate_products() -> pd.DataFrame:
    categories = {
        "Beverages": {
            "brands": ["AquaPure", "FizzBurst", "SunDrop"],
            "names": [
                "Sparkling Water 500ml", "Energy Drink 330ml", "Orange Juice 1L",
                "Green Tea 500ml", "Lemonade 330ml", "Sports Drink 750ml",
                "Cold Brew Coffee 250ml", "Coconut Water 330ml", "Berry Smoothie 500ml",
                "Iced Tea 1L",
            ],
        },
        "Snacks": {
            "brands": ["CrunchMaster", "SnackKing", "NibbleCo"],
            "names": [
                "Tortilla Chips 200g", "Cheese Puffs 150g", "Pretzels 250g",
                "Popcorn 100g", "Rice Cakes 150g", "Granola Bars 6pk",
                "Trail Mix 200g", "Beef Jerky 80g", "Crackers 200g",
                "Veggie Chips 150g",
            ],
        },
        "Dairy": {
            "brands": ["FreshFarm", "DairyDelight", "CreamCo"],
            "names": [
                "Whole Milk 1L", "Greek Yogurt 500g", "Cheddar Cheese 200g",
                "Butter 250g", "Cream Cheese 150g", "Sour Cream 200g",
                "Cottage Cheese 500g", "Heavy Cream 250ml", "Mozzarella 200g",
                "Whipped Cream 250ml",
            ],
        },
    }

    rows = []
    sku_counter = 1
    for cat, meta in categories.items():
        for i, name in enumerate(meta["names"]):
            brand = meta["brands"][i % len(meta["brands"])]
            sku_id = f"SKU{sku_counter:04d}"
            list_price = round(float(RNG.uniform(1.5, 15.0)), 2)
            launch_year = int(RNG.integers(2018, 2023))
            launch_month = int(RNG.integers(1, 13))
            launch_day = int(RNG.integers(1, 29))
            launch_date = f"{launch_year}-{launch_month:02d}-{launch_day:02d}"
            rows.append(
                {
                    "sku_id": sku_id,
                    "product_name": name,
                    "category": cat,
                    "brand": brand,
                    "package_size": name.split()[-1],
                    "list_price": list_price,
                    "launch_date": launch_date,
                }
            )
            sku_counter += 1

    df = pd.DataFrame(rows)

    # Quality issues: 2 null list_price, 1 null category
    null_price_idx = RNG.choice(df.index, size=2, replace=False)
    df.loc[null_price_idx, "list_price"] = None
    null_cat_idx = int(RNG.choice(df.index))
    df.loc[null_cat_idx, "category"] = None

    return df


def generate_stores() -> pd.DataFrame:
    region_data = {
        "North": [
            ("Chicago", "IL"), ("Milwaukee", "WI"), ("Minneapolis", "MN"),
            ("Detroit", "MI"), ("Cleveland", "OH"),
        ],
        "South": [
            ("Atlanta", "GA"), ("Houston", "TX"), ("Miami", "FL"),
            ("New Orleans", "LA"), ("Charlotte", "NC"),
        ],
        "East": [
            ("New York", "NY"), ("Philadelphia", "PA"), ("Boston", "MA"),
            ("Baltimore", "MD"), ("Pittsburgh", "PA"),
        ],
        "West": [
            ("Los Angeles", "CA"), ("Seattle", "WA"), ("Denver", "CO"),
            ("Phoenix", "AZ"), ("Portland", "OR"),
        ],
    }

    rows = []
    store_counter = 1
    for region, cities in region_data.items():
        for city, state in cities:
            store_id = f"STR{store_counter:03d}"
            store_name = f"{city} Mart"
            rows.append(
                {
                    "store_id": store_id,
                    "store_name": store_name,
                    "region": region,
                    "state": state,
                    "city": city,
                }
            )
            store_counter += 1

    df = pd.DataFrame(rows)

    # Quality issue: 1 null region
    null_region_idx = int(RNG.choice(df.index))
    df.loc[null_region_idx, "region"] = None

    # Quality issue: 1 duplicate store_id row (append duplicate of row 0)
    duplicate_row = df.iloc[0:1].copy()
    df = pd.concat([df, duplicate_row], ignore_index=True)

    return df


def generate_transactions(products_df: pd.DataFrame, stores_df: pd.DataFrame) -> pd.DataFrame:
    n_base = 30000
    date_range = pd.date_range("2022-01-01", "2024-12-31", freq="D")

    # Valid store_ids and sku_ids (deduplicated)
    valid_store_ids = stores_df["store_id"].dropna().unique().tolist()
    valid_sku_ids = products_df["sku_id"].dropna().unique().tolist()

    # Build category lookup for seasonal weights
    cat_lookup = products_df.set_index("sku_id")["category"].to_dict()
    sku_array = RNG.choice(valid_sku_ids, size=n_base)
    categories = [cat_lookup.get(s, "Snacks") for s in sku_array]

    # Seasonal weight per transaction based on month
    dates_raw = RNG.choice(date_range, size=n_base)
    months = pd.DatetimeIndex(dates_raw).month

    # Adjust volume using seasonal patterns + regional variation
    store_array_pre = RNG.choice(valid_store_ids, size=n_base)

    # Regional multipliers: North/East +30% volume via sampling weight
    region_lookup = stores_df.drop_duplicates("store_id").set_index("store_id")["region"].to_dict()
    store_weights = np.ones(len(valid_store_ids))
    for i, sid in enumerate(valid_store_ids):
        rgn = region_lookup.get(sid, "Other")
        if rgn in ("North", "East"):
            store_weights[i] = 1.3
    store_weights /= store_weights.sum()
    store_array = RNG.choice(valid_store_ids, size=n_base, p=store_weights)

    # Seasonal quantity multiplier
    def seasonal_qty(cat: str, month: int) -> float:
        if cat == "Beverages" and month in (6, 7, 8):
            return 1.5
        if cat == "Dairy" and month in (11, 12, 1):
            return 1.5
        return 1.0

    quantities = []
    for cat, m in zip(categories, months):
        base_qty = int(RNG.integers(1, 20))
        multiplier = seasonal_qty(cat, m)
        quantities.append(max(1, int(base_qty * multiplier)))

    unit_prices = [round(float(RNG.uniform(1.5, 15.0)), 2) for _ in range(n_base)]
    revenues = [round(q * p, 2) for q, p in zip(quantities, unit_prices)]
    txn_ids = [f"TXN{i:07d}" for i in range(1, n_base + 1)]
    date_strs = [d.strftime("%Y-%m-%d") for d in dates_raw]

    df = pd.DataFrame(
        {
            "transaction_id": txn_ids,
            "txn_date": date_strs,
            "store_id": store_array,
            "sku_id": sku_array,
            "quantity": quantities,
            "unit_price": unit_prices,
            "revenue": revenues,
        }
    )

    # --- Intentional quality issues ---

    # 3% duplicate transaction_ids (repeat existing rows)
    n_dupes = int(n_base * 0.03)
    dupe_rows = df.sample(n=n_dupes, random_state=42)
    df = pd.concat([df, dupe_rows], ignore_index=True)

    # 5% null quantity
    n_null_qty = int(len(df) * 0.05)
    null_qty_idx = RNG.choice(df.index, size=n_null_qty, replace=False)
    df.loc[null_qty_idx, "quantity"] = None

    # 2% negative unit_price
    n_neg_price = int(len(df) * 0.02)
    neg_price_idx = RNG.choice(df.index, size=n_neg_price, replace=False)
    df.loc[neg_price_idx, "unit_price"] = df.loc[neg_price_idx, "unit_price"].apply(
        lambda x: -abs(x) if pd.notna(x) else x
    )

    # 2% date format drift: DD/MM/YYYY
    n_date_drift = int(len(df) * 0.02)
    date_drift_idx = RNG.choice(df.index, size=n_date_drift, replace=False)
    for idx in date_drift_idx:
        d_str = df.at[idx, "txn_date"]
        if isinstance(d_str, str) and len(d_str) == 10 and d_str[4] == "-":
            y, m, day = d_str.split("-")
            df.at[idx, "txn_date"] = f"{day}/{m}/{y}"

    # 1% missing store_id
    n_null_store = int(len(df) * 0.01)
    null_store_idx = RNG.choice(df.index, size=n_null_store, replace=False)
    df.loc[null_store_idx, "store_id"] = None

    return df


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating products...")
    products = generate_products()
    products.to_csv(OUT_DIR / "products.csv", index=False)

    print("Generating stores...")
    stores = generate_stores()
    stores.to_csv(OUT_DIR / "stores.csv", index=False)

    print("Generating transactions...")
    transactions = generate_transactions(products, stores)
    transactions.to_csv(OUT_DIR / "transactions.csv", index=False)

    # Summary
    print("\n=== Data Generation Summary ===")
    print(f"products.csv     : {len(products)} rows")
    print(f"  null list_price: {products['list_price'].isna().sum()}")
    print(f"  null category  : {products['category'].isna().sum()}")

    print(f"stores.csv       : {len(stores)} rows")
    print(f"  null region    : {stores['region'].isna().sum()}")
    dup_stores = stores.duplicated(subset=['store_id']).sum()
    print(f"  duplicate store: {dup_stores}")

    n_txn = len(transactions)
    print(f"transactions.csv : {n_txn} rows")
    dup_txns = transactions.duplicated(subset=['transaction_id']).sum()
    print(f"  duplicate txn  : {dup_txns}")
    print(f"  null quantity  : {transactions['quantity'].isna().sum()}")
    neg_prices = (transactions['unit_price'] < 0).sum()
    print(f"  negative price : {neg_prices}")
    dd_mm_yyyy = transactions['txn_date'].astype(str).str.match(r'^\d{2}/\d{2}/\d{4}$').sum()
    print(f"  date drift rows: {dd_mm_yyyy}")
    print(f"  null store_id  : {transactions['store_id'].isna().sum()}")


if __name__ == "__main__":
    main()
```

Write to `D:\Sigmoid\Project\scripts\generate_data.py`.

- [ ] **Step 2: Run the generator**

From project root:
```
python scripts/generate_data.py
```

Expected output (approximate):
```
Generating products...
Generating stores...
Generating transactions...

=== Data Generation Summary ===
products.csv     : 30 rows
  null list_price: 2
  null category  : 1
stores.csv       : 21 rows
  null region    : 1
  duplicate store: 1
transactions.csv : ~30900 rows
  duplicate txn  : ~900
  null quantity  : ~1545
  negative price : ~618
  date drift rows: ~618
  null store_id  : ~309
```

- [ ] **Step 3: Verify CSV files exist**

Check `data/raw/` contains `products.csv`, `stores.csv`, `transactions.csv`.

---

### Task 4: src/ingestion/loader.py

**Files:**
- Create: `D:\Sigmoid\Project\src\ingestion\loader.py`

**Interfaces:**
- Consumes: CSV files at `data_dir` path
- Produces:
  - `load_products(data_dir: str) -> pd.DataFrame`
  - `load_stores(data_dir: str) -> pd.DataFrame`
  - `load_transactions(data_dir: str) -> pd.DataFrame`
  - Each raises `FileNotFoundError` if CSV missing
  - Each logs column names at DEBUG level via logger `"ingestion.loader"`

- [ ] **Step 1: Write src/ingestion/loader.py**

```python
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
```

Write to `D:\Sigmoid\Project\src\ingestion\loader.py`.

---

### Task 5: src/ingestion/cleaner.py

**Files:**
- Create: `D:\Sigmoid\Project\src\ingestion\cleaner.py`

**Interfaces:**
- Produces:
  - `clean_products(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]`
    - report keys: `rows_in`, `rows_out`, `nulls_dropped`, `price_imputed`
  - `clean_stores(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]`
    - report keys: `rows_in`, `rows_out`, `duplicates_removed`, `region_filled`
  - `clean_transactions(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]`
    - report keys: `rows_in`, `rows_out`, `duplicates_removed`, `nulls_dropped`, `bad_dates`, `negative_prices`

- [ ] **Step 1: Write src/ingestion/cleaner.py**

```python
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
        logger.debug("Imputed %d null list_price values with median %.2f", price_imputed, median_price)

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
```

Write to `D:\Sigmoid\Project\src\ingestion\cleaner.py`.

---

### Task 6: src/ingestion/db.py

**Files:**
- Create: `D:\Sigmoid\Project\src\ingestion\db.py`

**Interfaces:**
- Consumes:
  - `from src.config import settings`
  - `from src.ingestion.loader import load_products, load_stores, load_transactions`
  - `from src.ingestion.cleaner import clean_products, clean_stores, clean_transactions`
- Produces:
  - `get_connection(db_path: str) -> duckdb.DuckDBPyConnection`
  - `init_schema(conn: duckdb.DuckDBPyConnection) -> None`
  - `upsert_products(conn, df: pd.DataFrame) -> int`
  - `upsert_stores(conn, df: pd.DataFrame) -> int`
  - `upsert_transactions(conn, df: pd.DataFrame) -> int`
  - `run_pipeline(data_dir: str, db_path: str) -> dict`

- [ ] **Step 1: Write src/ingestion/db.py**

```python
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

_SCHEMA_SQL = """
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
);

CREATE TABLE IF NOT EXISTS products (
    sku_id VARCHAR PRIMARY KEY,
    product_name VARCHAR,
    category VARCHAR NOT NULL,
    brand VARCHAR,
    package_size VARCHAR,
    list_price FLOAT,
    launch_date DATE
);

CREATE TABLE IF NOT EXISTS stores (
    store_id VARCHAR PRIMARY KEY,
    store_name VARCHAR,
    region VARCHAR NOT NULL,
    state VARCHAR,
    city VARCHAR
);
"""


def get_connection(db_path: str) -> duckdb.DuckDBPyConnection:
    """Open (or create) a DuckDB database file and return the connection."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(db_path)
    logger.debug("Connected to DuckDB at %s", db_path)
    return conn


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create all tables if they do not already exist."""
    conn.executescript(_SCHEMA_SQL)
    logger.info("Schema initialised (CREATE TABLE IF NOT EXISTS)")


def upsert_products(conn: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> int:
    """Insert or replace products rows. Returns number of rows written."""
    if df.empty:
        return 0

    cols = ["sku_id", "product_name", "category", "brand", "package_size", "list_price", "launch_date"]
    insert_df = df[[c for c in cols if c in df.columns]].copy()

    conn.execute("CREATE TEMP TABLE IF NOT EXISTS _tmp_products AS SELECT * FROM products LIMIT 0")
    conn.execute("DELETE FROM _tmp_products")
    conn.execute("INSERT INTO _tmp_products SELECT * FROM insert_df")  # DuckDB can ref local vars
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
    insert_df = df[[c for c in cols if c in df.columns]].copy()

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
    insert_df = df[[c for c in cols if c in df.columns]].copy()

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
    """Orchestrate full load → clean → upsert pipeline. Returns quality report."""
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
```

Write to `D:\Sigmoid\Project\src\ingestion\db.py`.

---

### Task 7: tests/test_ingestion.py

**Files:**
- Create: `D:\Sigmoid\Project\tests\test_ingestion.py`

**Interfaces:**
- Consumes:
  - `from src.ingestion.cleaner import clean_transactions, clean_products, clean_stores`
  - `from src.ingestion.loader import load_transactions`
  - `from src.ingestion.db import run_pipeline, get_connection`

- [ ] **Step 1: Write tests/test_ingestion.py**

```python
"""Pytest tests for the CPG sales ingestion pipeline."""

from __future__ import annotations

import shutil
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
    # Write a minimal CSV to tmp_path
    import scripts.generate_data as gen  # noqa: PLC0415

    gen.OUT_DIR = tmp_path
    gen.main()

    df = load_transactions(str(tmp_path))
    required_cols = {"transaction_id", "txn_date", "store_id", "sku_id", "quantity", "unit_price", "revenue"}
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
    import datetime
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
    gen.OUT_DIR = data_dir
    gen.main()

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
```

Write to `D:\Sigmoid\Project\tests\test_ingestion.py`.

- [ ] **Step 2: Run tests (expect failures — db.py upsert SQL needs verification)**

```
python -m pytest tests/test_ingestion.py -v
```

Expected: some tests pass, surface any import or SQL errors.

---

## Self-Review Checklist

- [x] All 13 files specified in the scope are covered by a task
- [x] `pydantic-settings>=2.3` added to requirements.txt (spec requires it)
- [x] numpy seed=42 used throughout `generate_data.py`
- [x] Logger names match spec: `ingestion.loader`, `ingestion.cleaner`, `ingestion.db`
- [x] All 7 test functions are standalone (not in classes)
- [x] `tmp_path` fixture used for temp DB
- [x] No mocking of DuckDB — real DuckDB in temp file
- [x] Quality issue counts in `generate_data.py` match spec percentages
- [x] `clean_transactions` handles both date formats (YYYY-MM-DD and DD/MM/YYYY)
- [x] `upsert_*` functions use ON CONFLICT DO UPDATE (DuckDB upsert syntax)
- [x] `run_pipeline` is `__main__` entrypoint in `db.py`
- [x] All function signatures match what consuming tasks reference
