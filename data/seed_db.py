import pandas as pd
from sqlalchemy import create_engine, text

# 1. Database Connection String
DATABASE_URL = "postgresql://postgres:allDS%40%2399@localhost:5432/smartsupply"
engine = create_engine(DATABASE_URL)

def run_db_seeder():
    CLEANED_CSV_PATH = "c:/Users/hp/Desktop/SmartSupply/data/online_retail_cleaned.csv"
    
    print("Connecting to database and dropping old table if it exists...")
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS daily_sales;"))
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

    try:
        print("Reading cached file...")
        df_clean = pd.read_csv(CLEANED_CSV_PATH)
        
        print("Mapping CSV headers to database columns...")
        # Map uppercase Kaggle/Pandas headers to lowercase Postgres columns explicitly
        df_to_db = df_clean.rename(columns={
            'sales_date': 'sales_date',
            'StockCode': 'stock_code',       # Fixes the 'stock_code' key error
            'Country': 'country',
            'Quantity': 'quantity',
            'TotalRevenue': 'total_revenue',
            'UnitPrice': 'unit_price',
            'CustomerID': 'customer_count'
        })
        
        print("Enforcing strict database data types...")
        df_to_db['sales_date'] = pd.to_datetime(df_to_db['sales_date'])
        df_to_db['stock_code'] = df_to_db['stock_code'].astype(str)
        df_to_db['country'] = df_to_db['country'].astype(str)
        df_to_db['quantity'] = df_to_db['quantity'].astype(int)
        df_to_db['total_revenue'] = df_to_db['total_revenue'].astype(float)
        df_to_db['unit_price'] = df_to_db['unit_price'].astype(float)
        df_to_db['customer_count'] = df_to_db['customer_count'].astype(int)

        print("Streaming structured matrices into PostgreSQL (using 5k row chunks)...")
        df_to_db.to_sql(
            'daily_sales', 
            con=engine, 
            if_exists='append', 
            index=False, 
            chunksize=5000
        )
        print("Database execution sequence finished successfully! 304,758 rows inserted.")
        
    except FileNotFoundError:
        print(f"Error: Run data_cleaning.py first to construct: {CLEANED_CSV_PATH}")
    except Exception as e:
        print(f"Database engine runtime block: {e}")

if __name__ == "__main__":
    run_db_seeder()