import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from sqlalchemy import create_engine, text

# Import our finalized monolithic analytical functional layers
from config import DATABASE_URL
from data.ml_forecast import forecast_product_demand
from data.pricing_engine import calculate_dynamic_price
from data.llm_summary import generate_inventory_summary

# Initialize the FastAPI Enterprise App Gateway routing middleware
app = FastAPI(
    title="SmartSupply Core Engine",
    description="Autonomous Enterprise Inventory Optimization & Dynamic Elastic Pricing Data Pipeline",
    version="1.0.0"
)

# Enable declarative CORS settings for secure communication with Vite/React framework
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize global singleton relational database engines
db_engine = create_engine(DATABASE_URL)


# --- Strict Pydantic Modern Data Contract Validations ---
class PriceMetrics(BaseModel):
    original_price: float
    new_price: float
    price_change_percentage: float
    demand_velocity_ratio: float
    inventory_runway_days: float
    revenue_forecast_30d: float
    inventory_health_score: float
    restock_order_quantity: int
    reorder_priority: str
    forecast_confidence: float
    strategy_recommendation: str

class ForecastDay(BaseModel):
    date: str
    predicted_demand: float
    safety_floor: float
    safety_ceil: float

class InventoryPipelineResponse(BaseModel):
    stock_code: str
    metrics: PriceMetrics
    forecast_data: List[ForecastDay]
    executive_summary: str


# --- Core Functional Web Service Routes ---

@app.get("/")
def read_root():
    """System heartbeat route verification endpoint."""
    return {"status": "online", "engine": "SmartSupply Engine Enterprise Core v1.0"}


@app.get("/api/inventory/products")
def get_top_products():
    """
    Queries live PostgreSQL schemas to isolate high-volume transaction keys,
    safely handling fallback options if the catalog is offline.
    """
    try:
        query = text("""
            SELECT stock_code, COUNT(*) as txn_count 
            FROM daily_sales 
            GROUP BY stock_code 
            HAVING COUNT(*) >= 10
            ORDER BY txn_count DESC 
            LIMIT 25;
        """)
        
        with db_engine.connect() as connection:
            result = connection.execute(query)
            products = [row[0] for row in result.fetchall() if row[0] is not None]
            
        if not products:
            # Complete structural fallback list to guarantee component safety
            products = ["85123A", "84879", "22423", "47566", "20725", "22720", "22197"]
            
        return {"products": products}
    except Exception as db_err:
        print(f"[Database Catalog Warning] Falling back to standard stock indexes. Reason: {db_err}")
        return {"products": ["85123A", "84879", "22423", "47566", "20725", "22720", "22197"]}


@app.get("/api/inventory/forecast/{stock_code}", response_model=InventoryPipelineResponse)
def get_integrated_inventory_insights(stock_code: str):
    """
    Coordinates the predictive, optimizing, and generative pipeline:
    1. Runs Meta Prophet forecasting with automatic data aggregation and chronological date filling.
    2. Runs cost-aware dynamic matrix optimization equations.
    3. Triggers the generative AI asset to compile an executive briefing.
    """
    print(f"\n[Pipeline Trace] Executing Enterprise Intelligence Core for SKU: {stock_code}")
    
    # --- PHASE 1: DATABASE INTEGRATION AND LIVE STATE CAPTURE ---
    try:
        with db_engine.connect() as connection:
            # Query current warehouse indicators directly from the live layout
            inv_query = text("""
                SELECT current_stock 
                FROM inventory 
                WHERE stock_code = :stock_code 
                LIMIT 1;
            """)
            inv_res = connection.execute(inv_query, {"stock_code": stock_code}).fetchone()
    except Exception as conn_error:
        print(f"[CRITICAL] Database Connectivity Broken: {str(conn_error)}")
        raise HTTPException(status_code=503, detail="Database connection failed")

    # If the item doesn't exist in the warehouse ledger, assign a standard fallback configuration
    current_stock = float(inv_res[0]) if inv_res else 150.0

    # --- PHASE 2: PROPHEET TIME-SERIES CURVE FORECASTING ---
    forecast_df = forecast_product_demand(stock_code)
    
    # CRITICAL ERROR FIX: Handle NoneType or empty dataframes to prevent downstream attribute failures
    if forecast_df is None or forecast_df.empty:
        raise HTTPException(
            status_code=422, 
            detail="Not enough sales history to build predictive time-series trends"
        )
        
    # --- PHASE 3: CALCULATE DYNAMIC PRICING AND FINANCIAL METRICS ---
    try:
        # Safely extract historical baseline values from the input rows
        yhat_list = forecast_df['yhat'].head(7).tolist()
        historical_avg_7d = float(sum(yhat_list) / len(yhat_list)) if yhat_list else 1.0
        
        # Strip datetime index alignment issues by working with a clean index reset copy
        clean_df = forecast_df.reset_index(drop=True)
        
        # Run calculation calls using the updated 4-variable positioning layout
        pricing_data = calculate_dynamic_price(stock_code, clean_df, historical_avg_7d, current_stock)
    except Exception as pricing_err:
        print(f"[Engine Logic Error] Structural math crash: {str(pricing_err)}")
        raise HTTPException(status_code=500, detail="Pricing engine matrix optimization failed")

    # --- PHASE 4: STRUCTURING FORECAST RECORDS ---
    forecast_records = []
    # Capture the next 30 days of predictions to pass down to the UI charts
    future_records_df = clean_df.tail(30)
    for _, row in future_records_df.iterrows():
        forecast_records.append({
            "date": row['ds'].strftime('%Y-%m-%d'),
            "predicted_demand": round(max(0.0, row['yhat']), 2),
            "safety_floor": round(max(0.0, row['yhat_lower']), 2),
            "safety_ceil": round(max(0.0, row['yhat_upper']), 2)
        })

    if not forecast_records:
        raise HTTPException(status_code=404, detail="No upcoming timeline prediction insights found")

    # --- PHASE 5: RUN GENERATIVE AI AGENT SUMMARY ---
    executive_summary = generate_inventory_summary(stock_code, pricing_data)
    
    # --- PHASE 6: RETURN COMPLETE PAYLOAD DATA CONTRACT ---
    return {
        "stock_code": stock_code,
        "metrics": {
            "original_price": round(pricing_data["original_price"], 2),
            "new_price": round(pricing_data["new_price"], 2),
            "price_change_percentage": round(pricing_data["price_change_percentage"], 2),
            "demand_velocity_ratio": round(pricing_data["demand_velocity_ratio"], 2),
            "inventory_runway_days": round(pricing_data["inventory_runway_days"], 1),
            "revenue_forecast_30d": round(pricing_data["revenue_forecast_30d"], 2),
            "inventory_health_score": round(pricing_data["inventory_health_score"], 0),
            "restock_order_quantity": int(pricing_data["restock_order_quantity"]),
            "reorder_priority": pricing_data["reorder_priority"],
            "forecast_confidence": round(pricing_data["forecast_confidence"], 1),
            "strategy_recommendation": pricing_data["strategy_recommendation"]
        },
        "forecast_data": forecast_records,
        "executive_summary": executive_summary
    }


if __name__ == "__main__":
    import uvicorn
    # Start our local development network instance
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)