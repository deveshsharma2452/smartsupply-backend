import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from prophet import Prophet
from config import DATABASE_URL

def forecast_product_demand(stock_code: str) -> pd.DataFrame:
    """
    Extracts transaction quantities, groups multi-country records into single days,
    pads missing chronological intervals with zeros, and fits a Meta Prophet curve.
    """
    engine = create_engine(DATABASE_URL)
    
    # PARAMETERIZED QUERY: Blocks SQL injection vulnerabilities cleanly
    query = text("""
        SELECT CAST(sales_date AS DATE) as ds, SUM(quantity) as y
        FROM daily_sales
        WHERE stock_code = :stock_code
        GROUP BY CAST(sales_date AS DATE)
        ORDER BY ds ASC;
    """)
    
    try:
        with engine.connect() as connection:
            df = pd.read_sql_query(query, connection, params={"stock_code": stock_code})
            
        if df.empty or len(df) < 5:
            print(f"[Warning] Inadequate operational historical points for code: {stock_code}")
            return pd.DataFrame() # Controlled exit handling to prevent NoneType attribute crashes
            
        # Clear object indexing mappings and cast columns cleanly
        df['ds'] = pd.to_datetime(df['ds'])
        df['y'] = df['y'].astype(float)
        
        # CHRONOLOGICAL DATE PADDING LOGIC: Reconstruct missing date ranges with zero sales
        df = df.set_index('ds')
        complete_range = pd.date_range(start=df.index.min(), end=df.index.max(), freq='D')
        df = df.reindex(complete_range, fill_value=0.0).reset_index()
        df.columns = ['ds', 'y']
        
        # Fit and optimize the Prophet engine
        model = Prophet(yearly_seasonality=True, daily_seasonality=False, weekly_seasonality=True)
        model.fit(df)
        
        # Build 30-day forward projections
        future = model.make_future_dataframe(periods=30, freq='D')
        forecast = model.predict(future)
        
        # Return prediction intervals along with tracking points
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
        
    except Exception as err:
        print(f"[Core Forecast Exception] Execution halted for {stock_code}: {str(err)}")
        return pd.DataFrame()