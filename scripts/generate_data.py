"""Generate synthetic CPG sales data with intentional quality issues."""

from __future__ import annotations

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
                "Sparkling Water 500ml",
                "Energy Drink 330ml",
                "Orange Juice 1L",
                "Green Tea 500ml",
                "Lemonade 330ml",
                "Sports Drink 750ml",
                "Cold Brew Coffee 250ml",
                "Coconut Water 330ml",
                "Berry Smoothie 500ml",
                "Iced Tea 1L",
            ],
        },
        "Snacks": {
            "brands": ["CrunchMaster", "SnackKing", "NibbleCo"],
            "names": [
                "Tortilla Chips 200g",
                "Cheese Puffs 150g",
                "Pretzels 250g",
                "Popcorn 100g",
                "Rice Cakes 150g",
                "Granola Bars 6pk",
                "Trail Mix 200g",
                "Beef Jerky 80g",
                "Crackers 200g",
                "Veggie Chips 150g",
            ],
        },
        "Dairy": {
            "brands": ["FreshFarm", "DairyDelight", "CreamCo"],
            "names": [
                "Whole Milk 1L",
                "Greek Yogurt 500g",
                "Cheddar Cheese 200g",
                "Butter 250g",
                "Cream Cheese 150g",
                "Sour Cream 200g",
                "Cottage Cheese 500g",
                "Heavy Cream 250ml",
                "Mozzarella 200g",
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
            ("Chicago", "IL"),
            ("Milwaukee", "WI"),
            ("Minneapolis", "MN"),
            ("Detroit", "MI"),
            ("Cleveland", "OH"),
        ],
        "South": [
            ("Atlanta", "GA"),
            ("Houston", "TX"),
            ("Miami", "FL"),
            ("New Orleans", "LA"),
            ("Charlotte", "NC"),
        ],
        "East": [
            ("New York", "NY"),
            ("Philadelphia", "PA"),
            ("Boston", "MA"),
            ("Baltimore", "MD"),
            ("Pittsburgh", "PA"),
        ],
        "West": [
            ("Los Angeles", "CA"),
            ("Seattle", "WA"),
            ("Denver", "CO"),
            ("Phoenix", "AZ"),
            ("Portland", "OR"),
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
    date_strs = [pd.Timestamp(d).strftime("%Y-%m-%d") for d in dates_raw]

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
    dup_stores = stores.duplicated(subset=["store_id"]).sum()
    print(f"  duplicate store: {dup_stores}")

    n_txn = len(transactions)
    print(f"transactions.csv : {n_txn} rows")
    dup_txns = transactions.duplicated(subset=["transaction_id"]).sum()
    print(f"  duplicate txn  : {dup_txns}")
    print(f"  null quantity  : {transactions['quantity'].isna().sum()}")
    neg_prices = (transactions["unit_price"] < 0).sum()
    print(f"  negative price : {neg_prices}")
    dd_mm_yyyy = transactions["txn_date"].astype(str).str.match(r"^\d{2}/\d{2}/\d{4}$").sum()
    print(f"  date drift rows: {dd_mm_yyyy}")
    print(f"  null store_id  : {transactions['store_id'].isna().sum()}")


if __name__ == "__main__":
    main()
