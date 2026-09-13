import os
import pandas as pd


def clean_retail_data(input_path, output_path):
    """
    Cleans the Kaggle "Retail Store Inventory Forecasting Dataset"
    (https://www.kaggle.com/datasets/anirudhchauhan/retail-store-inventory-forecasting-dataset).

    Unlike the old Online Retail transaction-log dataset, this one is already
    daily-aggregated (one row per Store + Product + Date), so no groupby
    aggregation step is needed here — just column renaming, type
    enforcement, and basic sanity filtering.
    """
    print("--- Starting Data Cleaning Pipeline ---")

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Raw file not found at: {input_path}")

    df = pd.read_csv(input_path)
    initial_rows = len(df)

    required_cols = {
        "Date", "Store ID", "Product ID", "Category",
        "Inventory Level", "Units Sold", "Price",
    }
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(
            f"Input CSV is missing expected column(s): {sorted(missing)}. "
            f"Found columns: {list(df.columns)}"
        )

    # 1. Enforce types and clean text fields
    df["Date"] = pd.to_datetime(df["Date"])
    df["Product ID"] = df["Product ID"].astype(str).str.strip()
    df["Store ID"] = df["Store ID"].astype(str).str.strip()
    df["Category"] = df["Category"].astype(str).str.strip()

    # 2. Drop rows with non-physical values (negative sales/stock, zero/negative price)
    cleaned_df = df[
        (df["Units Sold"] >= 0)
        & (df["Inventory Level"] >= 0)
        & (df["Price"] > 0)
    ].copy()

    # 3. Derived revenue feature
    cleaned_df["TotalRevenue"] = cleaned_df["Units Sold"] * cleaned_df["Price"]

    # 4. Normalize naming convention for database mapping.
    # We keep Store-ID-level rows (not aggregated across stores) so the SQL
    # layer's GROUP BY / SUM logic naturally rolls stores up per SKU, exactly
    # like the old country-level rows did.
    cleaned_df = cleaned_df.rename(columns={
        "Date": "sales_date",
        "Product ID": "stock_code",
        "Store ID": "store_id",
        "Category": "category",
        "Inventory Level": "inventory_level",
        "Units Sold": "quantity",
        "Price": "unit_price",
        "TotalRevenue": "total_revenue",
    })

    output_cols = [
        "sales_date", "stock_code", "store_id", "category",
        "quantity", "unit_price", "total_revenue", "inventory_level",
    ]
    cleaned_df = cleaned_df[output_cols].sort_values("sales_date")

    cleaned_df.to_csv(output_path, index=False)

    dropped_rows = initial_rows - len(cleaned_df)
    print(f"Rows dropped due to invalid values: {dropped_rows} ({(dropped_rows / initial_rows) * 100:.2f}%)")
    print(f"Cleaned data shape: {cleaned_df.shape}")
    print(f"Cleaned data cached successfully at: {output_path}")
    print("--- Pipeline Execution Complete ---")


if __name__ == "__main__":
    # Paths are relative to this file's location, so this works on any machine/OS.
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    RAW_CSV = os.path.join(THIS_DIR, "retail_store_inventory.csv")
    CLEANED_CSV = os.path.join(THIS_DIR, "retail_store_inventory_cleaned.csv")

    clean_retail_data(RAW_CSV, CLEANED_CSV)
