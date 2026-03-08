import React, { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, Rectangle } from "react-leaflet";
import L from "leaflet";
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } from "recharts";

const CORE = process.env.REACT_APP_CORE_BASE || "http://localhost:8080";
const ANALYSIS = process.env.REACT_APP_ANALYSIS_BASE || "http://localhost:8000";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png"
});

function fmt(ts) {
  try { return new Date(ts).toLocaleString(); } catch { return String(ts); }
}

// Generates a color on a Blue -> Green -> Red gradient based on min/max bounds
// HSL logic: 240 (Blue) -> 120 (Green) -> 0 (Red)
function getColor(value, min, max) {
  if (min === max) return `hsl(120, 80%, 50%)`;
  const ratio = Math.max(0, Math.min(1, (value - min) / (max - min)));
  const hue = (1 - ratio) * 240;
  return `hsl(${hue}, 80%, 50%)`;
}

export default function App() {
  const [points, setPoints] = useState([]);
  const [metric, setMetric] = useState("temperature");
  const [choropleth, setChoropleth] = useState(null);
  const [selectedStation, setSelectedStation] = useState(null);
  const [series, setSeries] = useState([]);
  const [stats, setStats] = useState(null);
  const [loadingChoropleth, setLoadingChoropleth] = useState(false);
  
  // Predictive Map State
  const [hoursAhead, setHoursAhead] = useState(0);
  
  // Search State
  const [searchTxt, setSearchTxt] = useState("");
  const [mapRef, setMapRef] = useState(null);

  const center = useMemo(() => [45.07, 7.69], []);

  async function ingestNow() {
    await fetch(`${CORE}/api/ingest/realtime`, { method: "POST" });
    await refreshPoints();
  }

  async function refreshPoints() {
    const res = await fetch(`${CORE}/api/geo/latest?minutes=180&limit=2000`);
    const data = await res.json();
    setPoints(Array.isArray(data) ? data : []);
  }

  async function loadChoropleth() {
    if (points.length === 0) {
      setChoropleth(null);
      return;
    }
    setLoadingChoropleth(true);
    let minLat = 90, maxLat = -90, minLon = 180, maxLon = -180;
    for (let p of points) {
      if (p.lat != null && p.lon != null) {
        minLat = Math.min(minLat, p.lat);
        maxLat = Math.max(maxLat, p.lat);
        minLon = Math.min(minLon, p.lon);
        maxLon = Math.max(maxLon, p.lon);
      }
    }
    const padLat = (maxLat - minLat) * 0.15 || 0.15;
    const padLon = (maxLon - minLon) * 0.15 || 0.15;
    
    // Choose endpoint based on prediction slider
    const isForecast = hoursAhead > 0;
    const endpoint = isForecast ? "/choropleth/forecast" : "/choropleth";
    
    const params = new URLSearchParams({
      metric,
      minLat: minLat - padLat,
      maxLat: maxLat + padLat,
      minLon: minLon - padLon,
      maxLon: maxLon + padLon,
      nx: 25,
      ny: 25
    });
    
    if (isForecast) {
        params.append("hoursAhead", hoursAhead);
    }
    
    try {
      const res = await fetch(`${ANALYSIS}${endpoint}?${params.toString()}`);
      if (res.ok) {
        const gj = await res.json();
        setChoropleth({ gj, bounds: { minLat: minLat - padLat, maxLat: maxLat + padLat, minLon: minLon - padLon, maxLon: maxLon + padLon }, dims: {nx: 25, ny: 25} });
      } else {
        setChoropleth(null);
      }
    } catch {
      setChoropleth(null);
    } finally {
      setLoadingChoropleth(false);
    }
  }

  async function loadSeries(stationId, metricName) {
    const to = new Date().toISOString();
    const from = new Date(Date.now() - 24 * 3600 * 1000).toISOString();
    
    // Fetch History
    const res = await fetch(`${CORE}/api/series?stationId=${encodeURIComponent(stationId)}&from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`);
    const data = await res.json();
    const mapped = (Array.isArray(data) ? data : []).map(o => ({
      t: new Date(o.observedAt).getTime(),
      temperature: o.temperature,
      pressure: o.pressure,
      relativeHumidity: o.relativeHumidity,
      isForecast: false
    }));

    // Fetch Forecast
    let finalSeries = [...mapped];
    if (selectedStation && selectedStation.lat && selectedStation.lon) {
        try {
            const forecastRes = await fetch(`${ANALYSIS}/forecast`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    lat: selectedStation.lat, 
                    lon: selectedStation.lon, 
                    metric: metricName, 
                    hoursAhead: 24 
                })
            });
            
            if (forecastRes.ok) {
                const forecastData = await forecastRes.json();
                const projected = forecastData.forecast.map(fp => ({
                    t: fp.t,
                    [`${metricName}Prediction`]: fp.value,
                    isForecast: true
                }));
                finalSeries = [...finalSeries, ...projected];
            }
        } catch (e) {
            console.error("Forecast failed:", e);
        }
    }
    
    setSeries(finalSeries);
  }

  useEffect(() => {
    refreshPoints();
  }, []);

  useEffect(() => {
    setChoropleth(null);
    async function fetchStats() {
      try {
        const res = await fetch(`${ANALYSIS}/stats?metric=${metric}`);
        if (res.ok) {
          const data = await res.json();
          setStats(data);
        } else {
          setStats(null);
        }
      } catch (e) {
        setStats(null);
      }
    }
    fetchStats();
    
    if (selectedStation) {
      loadSeries(selectedStation.stationId || selectedStation.stationName, metric);
    }
  }, [metric, points, selectedStation]);

  // Optionally auto-reload choropleth when hoursAhead changes if the map is already active
  useEffect(() => {
    if (choropleth) {
        loadChoropleth();
    }
  }, [hoursAhead]);

  const choroplethNodes = useMemo(() => {
    if (!choropleth || !choropleth.gj.features || !stats) return [];
    
    const latStep = Math.abs(choropleth.bounds.maxLat - choropleth.bounds.minLat) / choropleth.dims.ny;
    const lonStep = Math.abs(choropleth.bounds.maxLon - choropleth.bounds.minLon) / choropleth.dims.nx;
    
    return choropleth.gj.features.map((f, i) => {
      const centerLon = f.geometry.coordinates[0];
      const centerLat = f.geometry.coordinates[1];
      const val = f.properties.value;
      
      const bounds = [
          [centerLat - latStep/2, centerLon - lonStep/2],
          [centerLat + latStep/2, centerLon + lonStep/2]
      ];
      
      return (
        <Rectangle
          key={`r-${i}`}
          bounds={bounds}
          pathOptions={{
              color: 'transparent',
              fillColor: getColor(val, stats.min, stats.max),
              fillOpacity: 0.45,
              weight: 0
          }}
        >
          <Tooltip>{hoursAhead > 0 ? 'Predicted' : 'Interpolated'} Value: {val != null ? val.toFixed(2) : '--'}</Tooltip>
        </Rectangle>
      );
    });
  }, [choropleth, stats, hoursAhead]);

  const searchResults = useMemo(() => {
    if (!searchTxt) return [];
    const lower = searchTxt.toLowerCase();
    return points.filter(p => 
      (p.city && p.city.toLowerCase().includes(lower)) || 
      (p.stationName && p.stationName.toLowerCase().includes(lower)) ||
      (p.stationId && p.stationId.toLowerCase().includes(lower))
    ).slice(0, 5); // top 5 results
  }, [searchTxt, points]);

  return (
    <div className="app-container">
      <div className="map-container" style={{ position: 'relative' }}>
        <MapContainer center={center} zoom={10} className="leaflet-container" ref={setMapRef}>
          <TileLayer
            attribution='&copy; OpenStreetMap contributors'
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          />

          {points.map((p, idx) => {
            const pos = [p.lat, p.lon];
            const label = p.stationId || p.stationName || `station-${idx}`;
            return (
              <Marker key={idx} position={pos} eventHandlers={{
                click: () => {
                  setSelectedStation(p);
                }
              }}>
                <Popup>
                  <div style={{ minWidth:220 }}>
                    <div><b>{label}</b></div>
                    <div>{p.city || ""}</div>
                    <div style={{ marginTop:6, fontSize: '0.9rem' }}><b>Datetime:</b> {fmt(p.observedAt)}</div>
                    <div style={{ fontSize: '0.9rem' }}><b>Temp:</b> {p.temperature ?? "—"} °C</div>
                    <div style={{ fontSize: '0.9rem' }}><b>RH:</b> {p.relativeHumidity ?? "—"} %</div>
                    <div style={{ fontSize: '0.9rem' }}><b>Pres:</b> {p.pressure ?? "—"} hPa</div>
                  </div>
                </Popup>
              </Marker>
            );
          })}

          {choroplethNodes}
        </MapContainer>

        {choropleth && stats && (
          <div className="map-legend">
            <div className="legend-title">Areal Map Legend ({metric})</div>
            <div className="legend-gradient"></div>
            <div className="legend-labels">
               <span>{stats.min != null ? stats.min.toFixed(1) : "--"} (Min)</span>
               <span>{stats.max != null ? stats.max.toFixed(1) : "--"} (Max)</span>
            </div>
            {hoursAhead > 0 && <div style={{textAlign: 'center', fontSize: '0.75rem', marginTop: 4, color: '#f59e0b', fontWeight: 'bold'}}>Showing T+{hoursAhead}h Prediction</div>}
          </div>
        )}
      </div>
      
      <div className="sidebar">
        <div className="sidebar-header">
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
             <h2>Meteo Platform</h2>
             <span className="badge-subtitle">Event-Driven</span>
          </div>
          <p style={{ margin: "4px 0 0", color: "var(--text-muted)", fontSize: "0.85rem" }}>
            Realtime Analytics & ML Forecasting
          </p>
          
          <div style={{ marginTop: '16px', position: 'relative' }}>
             <input 
               type="text" 
               className="search-input" 
               placeholder="Search by City or Station Name..." 
               value={searchTxt}
               onChange={e => setSearchTxt(e.target.value)}
             />
             {searchResults.length > 0 && (
               <ul className="suggestions-list">
                 {searchResults.map((res, i) => (
                   <li key={i} onClick={() => {
                      setSearchTxt("");
                      setSelectedStation(res);
                      if (mapRef) {
                        mapRef.flyTo([res.lat, res.lon], 13);
                      }
                   }}>
                      <b>{res.city || 'Unknown City'}</b> - {res.stationName || res.stationId}
                   </li>
                 ))}
               </ul>
             )}
          </div>
        </div>

        <div className="sidebar-content">
          <div className="btn-group">
            <button className="btn" onClick={refreshPoints}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 21v-5h5"/></svg>
              Refresh Data
            </button>
            <button className="btn btn-primary" onClick={ingestNow}>
              Force Ingestion
            </button>
          </div>

          <div className="card">
            <div className="card-title">
              Spatial Analytics & Map Prediction
            </div>
            <div className="form-group">
              <label>Metric Focus:</label>
              <select value={metric} onChange={e => setMetric(e.target.value)}>
                <option value="temperature">Temperature (°C)</option>
                <option value="pressure">Pressure (hPa)</option>
                <option value="relativeHumidity">Relative Humidity (%)</option>
              </select>
            </div>
            
            <div className="form-group" style={{ marginTop: '16px' }}>
              <label style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Predictive Time Slider:</span>
                <span style={{ color: hoursAhead > 0 ? '#f59e0b' : 'var(--text-muted)', fontWeight: hoursAhead > 0 ? 'bold' : 'normal' }}>
                  {hoursAhead === 0 ? "Now (Realtime)" : `+${hoursAhead} Hours`}
                </span>
              </label>
              <input 
                type="range" 
                min="0" max="24" step="1" 
                value={hoursAhead} 
                onChange={e => setHoursAhead(parseInt(e.target.value))}
                style={{ width: '100%', accentColor: hoursAhead > 0 ? '#f59e0b' : 'var(--primary)', cursor: 'pointer' }}
              />
            </div>
            
            {stats ? (
              <div className="metrics-grid">
                <div className="metric-box">
                  <span className="metric-label">Live Min</span>
                  <span className="metric-value">{stats.min?.toFixed(1) ?? "--"}</span>
                </div>
                <div className="metric-box">
                  <span className="metric-label">Live Max</span>
                  <span className="metric-value">{stats.max?.toFixed(1) ?? "--"}</span>
                </div>
                <div className="metric-box" style={{gridColumn: 'span 2'}}>
                  <span className="metric-label">Area Average (n={stats.count ?? 0})</span>
                  <span className="metric-value">{stats.avg?.toFixed(1) ?? "--"}</span>
                </div>
              </div>
            ) : (
              <div className="metric-box" style={{ textAlign: 'center', opacity: 0.6 }}>Loading Live Statistics...</div>
            )}

            <div className="btn-group" style={{ marginTop: '16px', marginBottom: 0 }}>
              <button className="btn btn-primary" onClick={loadChoropleth}>
                {loadingChoropleth ? 'Computing Map...' : hoursAhead > 0 ? 'Generate Predicted Map' : 'Generate Realtime Map'}
              </button>
              {choropleth && <button className="btn" onClick={() => setChoropleth(null)}>Clear</button>}
            </div>
          </div>

          <div className="card">
            <div className="card-title">
              History & Complete Weather Forecast
            </div>
            {!selectedStation ? (
              <div className="empty-state">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{marginBottom: 8, opacity:0.5}}><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
                <br />
                Search or select a station marker on the map to load its 24h history and 24h Open-Meteo forecast projection.
              </div>
            ) : (
              <>
                <div style={{ padding: '12px', background: 'rgba(255,255,255,0.05)', borderRadius: '8px', marginBottom: '16px', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: "1rem", color: "var(--text)", marginBottom: "8px", fontWeight: 'bold' }}>
                    📍 {selectedStation.city || "Unknown Location"} - {selectedStation.stationName || selectedStation.stationId}
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.85rem' }}>
                    <div><b>Timestamp:</b> {fmt(selectedStation.observedAt)}</div>
                    <div><b>Temp:</b> {selectedStation.temperature ?? "—"} °C</div>
                    <div><b>Humidity:</b> {selectedStation.relativeHumidity ?? "—"} %</div>
                    <div><b>Pressure:</b> {selectedStation.pressure ?? "—"} hPa</div>
                    <div><b>Lat:</b> {selectedStation.lat?.toFixed(4)}</div>
                    <div><b>Lon:</b> {selectedStation.lon?.toFixed(4)}</div>
                  </div>
                </div>
                
                <div style={{ height: 260, width: '100%', margin: "0 -8px" }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={series} margin={{top: 5, right: 20, left: -20, bottom: 0}}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                      <XAxis 
                        dataKey="t" 
                        tickFormatter={t => new Date(t).getHours() + ':00'} 
                        tick={{fontSize: 11, fill: '#64748b'}}
                        axisLine={false}
                        tickLine={false}
                        domain={['dataMin', 'dataMax']}
                        type="number"
                      />
                      <YAxis 
                         tick={{fontSize: 11, fill: '#64748b'}}
                         axisLine={false}
                         tickLine={false}
                         domain={['auto', 'auto']}
                      />
                      <Tooltip 
                        labelFormatter={fmt} 
                        contentStyle={{ borderRadius: 8, border: 'none', boxShadow: 'var(--shadow-md)', fontSize: '13px' }}
                      />
                      <Legend iconType="circle" wrapperStyle={{ fontSize: '12px', paddingTop: 10 }} />
                      <Line type="monotone" dataKey={metric} stroke="var(--primary)" strokeWidth={2} dot={false} name="History" />
                      <Line type="monotone" dataKey={`${metric}Prediction`} stroke="#f59e0b" strokeWidth={2} strokeDasharray="5 5" dot={false} name="Open-Meteo 24h Forecast" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </>
            )}
          </div>
          
        </div>
      </div>
    </div>
  );
}
