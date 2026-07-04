import os
from google import genai
from google.genai import types
from config import GEMINI_API_KEY

def generate_inventory_summary(stock_code: str, metrics: dict) -> str:
    """
    Triggers the Gemini Generative AI pipeline to compile an executive logistics
    brief based on statistical time-series metrics and cost-accounting parameters.
    """
    if not GEMINI_API_KEY:
        return (
            f"EXECUTIVE ADVISORY NOTICE [OFFLINE]: Product SKU {stock_code} is tracking at a "
            f"Dynamic Price point of ${metrics['new_price']:.2f} ({metrics['price_change_percentage']:.1f}% shift). "
            f"Inventory runways reflect {metrics['inventory_runway_days']:.1f} days of residual availability. "
            f"Please configure your local GEMINI_API_KEY environment variable to enable advanced AI-driven analysis."
        )
        
    try:
        # Initialize the modern, secure GenAI client interface
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Build a highly explicit context prompt to enforce rigorous analytical guardrails
        system_instruction = (
            "You are an elite Supply Chain AI Agent and Principal Retail Logistics Consultant. "
            "Your objective is to review statistical time-series forecasts and dynamic pricing data, "
            "then author a high-density, concise executive operational summary. Avoid generic platitudes. "
            "Address exact business trade-offs, margin improvements, and risk mitigation vectors."
        )
        
        prompt = f"""
        Analyze the following real-time inventory and pricing metrics for Product SKU: {stock_code}
        
        --- CRITICAL OPERATIONAL METRICS ---
        - Base Price: ${metrics['original_price']:.2f}
        - Optimized Target Price: ${metrics['new_price']:.2f}
        - Computed Price Shift: {metrics['price_change_percentage']:.2f}%
        - 7-Day Demand Velocity Ratio: {metrics['demand_velocity_ratio']:.2f}x vs baseline
        - Warehouse Stock Runway: {metrics['inventory_runway_days']:.2f} Days
        - Projected 30-Day Gross Revenue: ${metrics['revenue_forecast_30d']:.2f}
        - Inventory Operational Health Score: {metrics['inventory_health_score']:.0f}/100
        - Suggested Restock Order Volume: {metrics['restock_order_quantity']:.0f} units
        - Automated Supply Chain Priority Level: {metrics['reorder_priority']}
        - Prophet Statistical Forecast Confidence: {metrics['forecast_confidence']:.1f}%
        
        --- OUTPUT FORMAT REQUIREMENTS ---
        Write a concise 3 to 4 sentence executive paragraph. 
        1. Diagnose the current demand velocity vs stock runway reality.
        2. Justify the dynamic pricing optimization strategy based on margin safety or liquidation needs.
        3. Deliver an explicit instruction regarding the suggested restock order volume and priority vector.
        Do not use markdown bolding formatting indicators (like '**') anywhere in the text body response.
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3, # Low temperature forces analytical, data-grounded consistency
                max_output_tokens=350
            )
        )
        
        if response.text:
            return response.text.strip()
        return "Error: Generative model returned an empty string signature payload."
        
    except Exception as gemini_err:
        print(f"[Gemini Framework Exception] Operational pipeline fallback triggered: {str(gemini_err)}")
        return (
            f"SUPPLY CHAIN WARNING: Advanced text generation pipeline is currently experiencing connection drops. "
            f"Product {stock_code} reflects a calculated restock target of {metrics['restock_order_quantity']} units "
            f"under {metrics['reorder_priority']} priority criteria to preserve continuous market alignment."
        )