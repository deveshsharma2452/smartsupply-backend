import os
import sys

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

# Make sure the repo root (where config.py lives) is importable, whether this
# script is run as `python data/seed_db.py` or `python -m data.seed_db`.
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(THIS_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import DATABASE_URL  # noqa: E402  (import after sys.path fix, intentional)

CLEANED_CSV_PATH = os.path.join(THIS_DIR, "online_retail_cleaned.csv")

engine = create_engine(DATABASE_URL)


def create_schema(conn):
    """Create both tables the app depends on. `inventory` was previously
    missing entirely, which caused /api/inventory/forecast/{stock_code} to
    error out at query time."""
    conn.execute(text("DROP TABLE IF EXISTS daily_sales;"))
    conn.execute(text("DROP TABLE IF EXISTS inventory;"))

    conn.execute(text("""
        CREATE TABLE daily_sales (
            id SERIAL PRIMARY KEY,
            sales_date TIMESTAMP NOT NULL,
            stock_code VARCHAR(50) NOT NULL,
            country VARCHAR(100) NOT NULL,
            quantity INTEGER NOT NULL,
            total_revenue FLOAT NOT NULL,
            unit_price FLOAT NOT NULL,
            customer_count INTEGER NOT NULL
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
    df_to_db = df_clean.rename(columns={
        'sales_date': 'sales_date',
        'StockCode': 'stock_code',
        'Country': 'country',
        'Quantity': 'quantity',
        'TotalRevenue': 'total_revenue',
        'UnitPrice': 'unit_price',
        'CustomerID': 'customer_count'
    })

    df_to_db['sales_date'] = pd.to_datetime(df_to_db['sales_date'])
    df_to_db['stock_code'] = df_to_db['stock_code'].astype(str)
    df_to_db['country'] = df_to_db['country'].astype(str)
    df_to_db['quantity'] = df_to_db['quantity'].astype(int)
    df_to_db['total_revenue'] = df_to_db['total_revenue'].astype(float)
    df_to_db['unit_price'] = df_to_db['unit_price'].astype(float)
    df_to_db['customer_count'] = df_to_db['customer_count'].astype(int)

    df_to_db.to_sql(
        'daily_sales',
        con=engine,
        if_exists='append',
        index=False,
        chunksize=5000
    )
    return df_to_db


def build_inventory_rows(df_to_db: pd.DataFrame) -> pd.DataFrame:
    """The source dataset (Online Retail) has no real warehouse stock levels,
    so we synthesize plausible ones per SKU from its own sales history:
      - unit_cost      = 60% of the SKU's average selling price
      - minimum_stock  = ~14 days of average daily demand (reorder point)
      - current_stock  = a randomized multiple of minimum_stock, so some
                          SKUs land in CRITICAL/HIGH reorder territory and
                          others don't (useful for demoing the pricing engine)
    """
    rng = np.random.default_rng(42)  # seeded for reproducible demo data

    per_sku = df_to_db.groupby('stock_code').agg(
        avg_unit_price=('unit_price', 'mean'),
        total_quantity=('quantity', 'sum'),
        days_active=('sales_date', 'nunique'),
    ).reset_index()

    per_sku['avg_daily_demand'] = per_sku['total_quantity'] / per_sku['days_active'].clip(lower=1)
    per_sku['unit_cost'] = (per_sku['avg_unit_price'] * 0.60).round(2)
    per_sku['minimum_stock'] = (per_sku['avg_daily_demand'] * 14).clip(lower=10).round(0)

    stock_multiplier = rng.uniform(0.3, 3.0, size=len(per_sku))
    per_sku['current_stock'] = (per_sku['minimum_stock'] * stock_multiplier).round(0)

    return per_sku[['stock_code', 'current_stock', 'unit_cost', 'minimum_stock']]


def run_db_seeder():
    print("Connecting to database and rebuilding schema (daily_sales + inventory)...")
    with engine.begin() as conn:
        create_schema(conn)

    try:
        print(f"Reading cleaned file from: {CLEANED_CSV_PATH}")
        df_clean = pd.read_csv(CLEANED_CSV_PATH)

        print("Loading daily_sales...")
        df_to_db = load_daily_sales(df_clean)
        print(f"daily_sales: {len(df_to_db)} rows inserted.")

        print("Deriving and loading inventory levels per SKU...")
        inventory_df = build_inventory_rows(df_to_db)
        inventory_df.to_sql('inventory', con=engine, if_exists='append', index=False)
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
