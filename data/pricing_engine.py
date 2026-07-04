import pandas as pd
from sqlalchemy import create_engine, text
from config import DATABASE_URL

def calculate_dynamic_price(stock_code: str, forecast_df: pd.DataFrame, historical_avg_7d: float, current_stock: float) -> dict:
    """
    Calculates cost margins by combining demand variations with live inventory levels.
    """
    engine = create_engine(DATABASE_URL)
    
    # Pull current product prices and cost parameters directly from the tables
    query = text("""
        SELECT DISTINCT d.unit_price, i.unit_cost, i.minimum_stock 
        FROM daily_sales d
        JOIN inventory i ON d.stock_code = i.stock_code
        WHERE i.stock_code = :stock_code 
        LIMIT 1;
    """)
    
    # Sensible system configuration fallbacks
    original_price = 10.0
    unit_cost = 6.0
    minimum_stock = 50.0
    
    try:
        with engine.connect() as connection:
            res = connection.execute(query, {"stock_code": stock_code}).fetchone()
            if res:
                original_price = float(res[0] or 10.0)
                unit_cost = float(res[1] or (original_price * 0.60))
                minimum_stock = float(res[2] or 50.0)
    except Exception as e:
        print(f"[Pricing Engine Exception] Falling back to default baseline ratios: {e}")

    # Extract forward metrics safely from the time-series predictions
    future_30d = forecast_df.tail(30)
    predicted_demand_30d = float(future_30d['yhat'].sum())
    predicted_demand_7d = float(future_30d['yhat'].head(7).sum())
    
    # Calculate operational safety values
    # Confidence interval width = Upper Bound - Lower Bound
    interval_width = (future_30d['yhat_upper'] - future_30d['yhat_lower']).mean()
    forecast_confidence = max(0.1, min(0.98, 1.0 - (interval_width / (future_30d['yhat'].mean() + 1.0))))
    
    # Determine the rate of demand change
    demand_velocity_ratio = predicted_demand_7d / (historical_avg_7d * 7.0 + 1.0)
    demand_velocity_ratio = max(0.2, min(5.0, demand_velocity_ratio)) # Keep metrics bounded
    
    # Calculate stock depletion windows
    daily_burn_rate = predicted_demand_30d / 30.0
    inventory_runway_days = current_stock / (daily_burn_rate + 0.001)
    inventory_runway_days = max(0.0, min(365.0, inventory_runway_days))
    
    # High-impact metric calculation updates (Revenue Forecast and Inventory Health)
    revenue_forecast_30d = predicted_demand_30d * original_price
    
    # Calculate Inventory Health Score
    health_deductions = 0
    if current_stock < minimum_stock:
        health_deductions += 40 # Critical stockout risk
    elif current_stock > (minimum_stock * 5):
        health_deductions += 20 # Excess holding costs
        
    if inventory_runway_days < 7:
        health_deductions += 30
        
    inventory_health_score = max(10, min(100, 100 - health_deductions))
    
    # Calculate accurate restock quantities
    restock_order_quantity = 0
    reorder_priority = "OPTIMAL"
    
    if current_stock <= minimum_stock or inventory_runway_days <= 10:
        # Buffer targets = Target runway coverage + safety baseline
        target_stock_buffer = (daily_burn_rate * 21) + minimum_stock
        restock_order_quantity = int(max(0.0, target_stock_buffer - current_stock))
        reorder_priority = "CRITICAL" if inventory_runway_days <= 5 else "HIGH"
    elif current_stock < (minimum_stock * 1.5):
        restock_order_quantity = int(max(0.0, (daily_burn_rate * 14) - current_stock))
        reorder_priority = "MEDIUM"

    # Elastic dynamic price logic adjustments
    price_modifier = 0.0
    if demand_velocity_ratio > 1.2 and current_stock > 0:
        price_modifier += 0.15 # Increase price during high demand periods
    if inventory_runway_days < 10:
        price_modifier += 0.10 # Safeguard inventory levels
    if inventory_runway_days > 60:
        price_modifier -= 0.15 # Lower price to clear excess inventory
        
    new_price = max(unit_cost * 1.15, original_price * (1.0 + price_modifier))
    price_change_percentage = ((new_price - original_price) / original_price) * 100.0
    
    # Map recommendations to your operational priorities
    strategy_rec = "MAINTAIN PRICE BASELINE"
    if price_change_percentage > 5.0:
        strategy_rec = "RAISE PRICE: CAPTURE MARGIN"
    elif price_change_percentage < -5.0:
        strategy_rec = "DISCOUNT PRICE: LIQUIDATE STOCK"

    return {
        "original_price": original_price,
        "new_price": new_price,
        "price_change_percentage": price_change_percentage,
        "demand_velocity_ratio": demand_velocity_ratio,
        "inventory_runway_days": inventory_runway_days,
        "revenue_forecast_30d": revenue_forecast_30d,
        "inventory_health_score": inventory_health_score,
        "restock_order_quantity": restock_order_quantity,
        "reorder_priority": reorder_priority,
        "forecast_confidence": forecast_confidence * 100.0,
        "strategy_recommendation": strategy_rec
    }