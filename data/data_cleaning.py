import os
import pandas as pd

def clean_retail_data(input_path, output_path):
    print("--- Starting Brutal Data Cleaning Pipeline ---")
    
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Raw file not found at: {input_path}")
        
    # 1. Load raw transaction records
    df = pd.read_csv(input_path)
    initial_rows = len(df)
    
    # 2. Enforce strict data types and clean text spaces
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    df['StockCode'] = df['StockCode'].astype(str).str.strip()
    df['InvoiceNo'] = df['InvoiceNo'].astype(str).str.strip()
    
    # 3. Handle missing customer entries explicitly
    df['CustomerID'] = df['CustomerID'].fillna(-1).astype(int)
    
    # 4. Remove bad accounting, zero values, and order cancellations
    cleaned_df = df[
        (df['Quantity'] > 0) & 
        (df['UnitPrice'] > 0) & 
        (df['UnitPrice'] < 10000) &
        (~df['InvoiceNo'].str.startswith('C', na=False))
    ].copy()
    
    # 5. Extract the revenue feature
    cleaned_df['TotalRevenue'] = cleaned_df['Quantity'] * cleaned_df['UnitPrice']
    
    # 6. Compress and group into a daily transactional matrix
    daily_aggregated = cleaned_df.groupby([
        cleaned_df['InvoiceDate'].dt.date, 
        'StockCode', 
        'Country'
    ]).agg({
        'Quantity': 'sum',
        'TotalRevenue': 'sum',
        'UnitPrice': 'mean',          
        'CustomerID': lambda x: (x != -1).sum() 
    }).reset_index()
    
    # Normalize naming convention for database mapping
    daily_aggregated.rename(columns={'InvoiceDate': 'sales_date'}, inplace=True)
    daily_aggregated['sales_date'] = pd.to_datetime(daily_aggregated['sales_date'])
    
    # 7. Write clean dataset to local storage cache
    daily_aggregated.to_csv(output_path, index=False)
    
    dropped_rows = initial_rows - len(cleaned_df)
    print(f"Rows dropped due to anomalies/cancellations: {dropped_rows} ({(dropped_rows/initial_rows)*100:.2f}%)")
    print(f"Cleaned matrix shape: {daily_aggregated.shape}")
    print(f"Cleaned data cached successfully at: {output_path}")
    print("--- Pipeline Execution Complete ---")

if __name__ == "__main__":
    # Adjust paths based on local environment setups if necessary
    RAW_CSV = "c:/Users/hp/Desktop/SmartSupply/data/online_retail.csv"
    CLEANED_CSV = "c:/Users/hp/Desktop/SmartSupply/data/online_retail_cleaned.csv"
    
    clean_retail_data(RAW_CSV, CLEANED_CSV)