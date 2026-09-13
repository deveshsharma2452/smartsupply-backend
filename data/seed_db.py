import os
import sys

import pandas as pd
from sqlalchemy import create_engine, text

# Make sure the repo root (where config.py lives) is importable, whether this
# script is run as `python data/seed_db.py` or `python -m data.seed_db`.
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(THIS_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import DATABASE_URL  # noqa: E402  (import after sys.path fix, intentional)

CLEANED_CSV_PATH = os.path.join(THIS_DIR, "retail_store_inventory_cleaned.csv")

engine = create_engine(DATABASE_URL)


def create_schema(conn):
    """`inventory` and `daily_sales` keep the exact same shape as before, so
    main.py and pricing_engine.py don't need any changes for the new dataset."""
    conn.execute(text("DROP TABLE IF EXISTS daily_sales;"))
    conn.execute(text("DROP TABLE IF EXISTS inventory;"))

    conn.execute(text("""
        CREATE TABLE daily_sales (
            id SERIAL PRIMARY KEY,
            sales_date TIMESTAMP NOT NULL,
            stock_code VARCHAR(50) NOT NULL,
            store_id VARCHAR(50) NOT NULL,
            category VARCHAR(100) NOT NULL,
            quantity INTEGER NOT NULL,
            total_revenue FLOAT NOT NULL,
            unit_price FLOAT NOT NULL
        );
    """))
    conn.execute(text("CREATE INDEX idx_stock_code ON daily_sales(stock_code);"))
    conn.execute(text("CREATE INDEX idx_sales_date ON daily_sales(sales_date);"))

    conn.execute(text("""
        CREATE TABLE inventory (
            stock_code VARCHAR(50) PRIMARY KEY,
            current_stock FLOAT NOT NULL,
            unit_cost FLOAT NOT NULL,
            minimum_stock FLOAT NOT NULL
        );
    """))


def load_daily_sales(df_clean: pd.DataFrame) -> pd.DataFrame:
    df_to_db = df_clean[[
        "sales_date", "stock_code", "store_id", "category",
        "quantity", "unit_price", "total_revenue",
    ]].copy()

    df_to_db["sales_date"] = pd.to_datetime(df_to_db["sales_date"])
    df_to_db["stock_code"] = df_to_db["stock_code"].astype(str)
    df_to_db["store_id"] = df_to_db["store_id"].astype(str)
    df_to_db["category"] = df_to_db["category"].astype(str)
    df_to_db["quantity"] = df_to_db["quantity"].astype(int)
    df_to_db["unit_price"] = df_to_db["unit_price"].astype(float)
    df_to_db["total_revenue"] = df_to_db["total_revenue"].astype(float)

    df_to_db.to_sql(
        "daily_sales",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=5000,
    )
    return df_to_db


def build_inventory_rows(df_clean: pd.DataFrame) -> pd.DataFrame:
    """
    Unlike the old Online Retail dataset, this dataset has a REAL
    `inventory_level` column per store/product/day, so current stock is no
    longer invented:
      - current_stock = sum of each SKU's `inventory_level` across all
                         stores, on the most recent date in the data
      - unit_cost      = still an assumption (60% of the SKU's average
                         selling price) — this dataset has no real cost field
      - minimum_stock  = still a heuristic (~14 days of average daily
                         demand as a reorder point) — no real reorder-point
                         field is provided either
    """
    latest_date = df_clean["sales_date"].max()
    latest_snapshot = df_clean[df_clean["sales_date"] == latest_date]

    current_stock = (
        latest_snapshot.groupby("stock_code")["inventory_level"]
        .sum()
        .rename("current_stock")
    )

    per_sku_demand = df_clean.groupby("stock_code").agg(
        avg_unit_price=("unit_price", "mean"),
        total_quantity=("quantity", "sum"),
        days_active=("sales_date", "nunique"),
    )
    per_sku_demand["avg_daily_demand"] = (
        per_sku_demand["total_quantity"] / per_sku_demand["days_active"].clip(lower=1)
    )
    per_sku_demand["unit_cost"] = (per_sku_demand["avg_unit_price"] * 0.60).round(2)
    per_sku_demand["minimum_stock"] = (
        (per_sku_demand["avg_daily_demand"] * 14).clip(lower=10).round(0)
    )

    inventory_df = per_sku_demand.join(current_stock, how="left").reset_index()
    inventory_df["current_stock"] = inventory_df["current_stock"].fillna(0).round(0)

    return inventory_df[["stock_code", "current_stock", "unit_cost", "minimum_stock"]]


def run_db_seeder():
    print("Connecting to database and rebuilding schema (daily_sales + inventory)...")
    with engine.begin() as conn:
        create_schema(conn)

    try:
        print(f"Reading cleaned file from: {CLEANED_CSV_PATH}")
        df_clean = pd.read_csv(CLEANED_CSV_PATH, parse_dates=["sales_date"])

        print("Loading daily_sales...")
        df_to_db = load_daily_sales(df_clean)
        print(f"daily_sales: {len(df_to_db)} rows inserted.")

        print("Deriving and loading inventory levels per SKU...")
        inventory_df = build_inventory_rows(df_clean)
        inventory_df.to_sql("inventory", con=engine, if_exists="append", index=False)
        print(f"inventory: {len(inventory_df)} SKU rows inserted.")

        print("Database seed complete.")

    except FileNotFoundError:
        print(
            f"Error: cleaned CSV not found at {CLEANED_CSV_PATH}. "
            f"Run `python data/data_cleaning.py` first to generate it."
        )
    except Exception as e:
        print(f"Database engine runtime error: {e}")


if __name__ == "__main__":
    run_db_seeder()
