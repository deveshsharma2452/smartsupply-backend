import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import './App.css';

export default function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedCode, setSelectedCode] = useState('85123A');
  const [productList, setProductList] = useState(["85123A"]);

  const fetchProductCatalog = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/inventory/products');
      if (response.ok) {
        const json = await response.json();
        setProductList(json.products);
        if (json.products?.length > 0) setSelectedCode(json.products[0]);
      }
    } catch (err) {
      console.error("Database initialization connection error:", err);
    }
  };

  const executePipelineAnalysis = async (code) => {
    if (!code) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/inventory/forecast/${code}`);
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Database query analysis breakdown.");
      }
      const json = await response.json();
      setData(json);
    } catch (err) {
      setError(err.message);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchProductCatalog(); }, []);

  // Compute total upcoming forecast aggregates for the grid summary cards
  const computeTotalForecastDemand = (records) => {
    if (!records) return "0 Units";
    const total = records.reduce((sum, item) => sum + item.predicted_demand, 0);
    return `${Math.round(total).toLocaleString()} Units`;
  };

  return (
    <div className="app-container">
      <div className="layout-max-width">
        
        {/* Core Title Panel Block */}
        <header className="hero-header">
          <h1 className="hero-title">SmartSupply AI Engine</h1>
          <p className="hero-subtitle">AI-powered Demand Forecasting • Dynamic Pricing • Inventory Optimization</p>
        </header>

        {/* Selection Execution Form Bar */}
        <section className="control-bar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ color: '#94a3b8', fontSize: '0.95rem' }}>Product</span>
            <select 
              value={selectedCode}
              onChange={(e) => setSelectedCode(e.target.value)}
              className="custom-select"
              disabled={loading}
            >
              {productList.map(code => <option key={code} value={code}>{code}</option>)}
            </select>
          </div>
          <button onClick={() => executePipelineAnalysis(selectedCode)} disabled={loading} className="action-btn">
            {loading ? 'Analyzing...' : 'Analyze Product'}
          </button>
        </section>

        <hr className="horizontal-divider" />

        {/* Dynamic Workspace Matrix Content */}
        {error && (
          <div style={{ color: '#f87171', backgroundColor: 'rgba(239,68,68,0.1)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(239,68,68,0.2)', marginBottom: '2rem' }}>
            <strong>System Error:</strong> {error}
          </div>
        )}

        {data && !loading && (
          <div>
            
            {/* 4x2 Metric Row Grid Mapping */}
            <section className="metric-grid-4x2">
              {/* Row 1 cards */}
              <div className="metric-card">
                <div className="metric-title">Forecast Demand</div>
                <div className="metric-data">{computeTotalForecastDemand(data.forecast_data)}</div>
              </div>
              <div className="metric-card">
                <div className="metric-title">Dynamic Price</div>
                <div className="metric-data">${data.metrics.new_price.toFixed(2)}</div>
              </div>
              <div className="metric-card">
                <div className="metric-title">Health Score</div>
                <div className="metric-data">{data.metrics.inventory_health_score}/100</div>
              </div>
              <div className="metric-card">
                <div className="metric-title">Stock Status</div>
                <div className="metric-data">{data.metrics.inventory_runway_days} Days Left</div>
              </div>

              {/* Row 2 cards */}
              <div className="metric-card">
                <div className="metric-title">Revenue Forecast</div>
                <div className="metric-data">${Math.round(data.metrics.revenue_forecast_30d).toLocaleString()}</div>
              </div>
              <div className="metric-card">
                <div className="metric-title">Confidence</div>
                <div className="metric-data">{Math.round(data.metrics.forecast_confidence)}%</div>
              </div>
              <div className="metric-card">
                <div className="metric-title">Restock Qty</div>
                <div className="metric-data">{data.metrics.restock_order_quantity} Units</div>
              </div>
              <div className="metric-card">
                <div className="metric-title">Strategy</div>
                <div className="metric-data" style={{ fontSize: '1.25rem', color: '#818cf8', marginTop: '0.8rem' }}>
                  {data.metrics.strategy_recommendation}
                </div>
              </div>
            </section>

            <hr className="horizontal-divider" />

            {/* Time-Series Graph Frame Area */}
            <section className="section-wrapper">
              <h3 className="section-label">30 Day Demand Forecast</h3>
              <div className="display-panel" style={{ height: '320px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.forecast_data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="prophetGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#4f46e5" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                    <XAxis dataKey="date" stroke="#64748b" tickLine={false} style={{ fontSize: '12px' }} />
                    <YAxis stroke="#64748b" tickLine={false} style={{ fontSize: '12px' }} />
                    <Tooltip contentStyle={{ backgroundColor: '#111a36', borderColor: '#334155', color: '#fff' }} />
                    <Area type="monotone" dataKey="predicted_demand" name="Demand Forecast" stroke="#4f46e5" strokeWidth={2.5} fillOpacity={1} fill="url(#prophetGradient)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </section>

            <hr className="horizontal-divider" />

            {/* AI Summary Frame Panel */}
            <section className="section-wrapper">
              <h3 className="section-label">AI Executive Summary</h3>
              <div className="display-panel" style={{ color: '#cbd5e1', fontSize: '1.05rem', lineHeight: '1.7', letterSpacing: '0.01em' }}>
                {data.executive_summary}
              </div>
            </section>

            <hr className="horizontal-divider" />

            {/* Detailed Forecast Tabular Layout */}
            <section className="section-wrapper">
              <h3 className="section-label">Detailed Forecast Table</h3>
              <div className="display-panel" style={{ padding: '0.5rem', overflowX: 'auto' }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Demand</th>
                      <th>Lower Bound</th>
                      <th>Upper Bound</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.forecast_data.map((row, idx) => (
                      <tr key={idx}>
                        <td style={{ fontFamily: 'monospace', fontWeight: '600', color: '#cbd5e1' }}>{row.date}</td>
                        <td style={{ color: '#ffffff', fontWeight: '700' }}>{Math.round(row.predicted_demand)}</td>
                        <td style={{ color: '#64748b' }}>{Math.round(row.safety_floor)}</td>
                        <td style={{ color: '#64748b' }}>{Math.round(row.safety_ceil)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

          </div>
        )}
      </div>
    </div>
  );
}