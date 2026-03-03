import React, { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, CircleMarker } from "react-leaflet";
import L from "leaflet";
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend } from "recharts";

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

export default function App() {
  const [points, setPoints] = useState([]);
  const [metric, setMetric] = useState("temperature");
  const [choropleth, setChoropleth] = useState(null);
  const [selectedStation, setSelectedStation] = useState(null);
  const [series, setSeries] = useState([]);

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
    const res = await fetch(`${ANALYSIS}/choropleth?metric=${metric}`);
    const gj = await res.json();
    setChoropleth(gj);
  }

  async function loadSeries(stationId) {
    const to = new Date().toISOString();
    const from = new Date(Date.now() - 24*3600*1000).toISOString();
    const res = await fetch(`${CORE}/api/series?stationId=${encodeURIComponent(stationId)}&from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`);
    const data = await res.json();
    const mapped = (Array.isArray(data) ? data : []).map(o => ({
      t: o.observedAt,
      temperature: o.temperature,
      pressure: o.pressure,
      relativeHumidity: o.relativeHumidity
    }));
    setSeries(mapped);
  }

  useEffect(() => {
    refreshPoints();
  }, []);

  useEffect(() => {
    setChoropleth(null);
  }, [metric]);

  const choroplethPts = useMemo(() => {
    if (!choropleth || !choropleth.features) return [];
    return choropleth.features.map(f => ({
      lat: f.geometry.coordinates[1],
      lon: f.geometry.coordinates[0],
      value: f.properties.value
    }));
  }, [choropleth]);

  return (
    <div style={{ display:"grid", gridTemplateColumns:"380px 1fr", height:"100vh" }}>
      <div style={{ padding:16, borderRight:"1px solid #eee", overflow:"auto" }}>
        <h2 style={{ marginTop:0 }}>Meteo Platform</h2>
        <p style={{ marginTop:0, color:"#555" }}>
          2 microservizi + TimescaleDB + RabbitMQ (event-driven)
        </p>

        <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
          <button onClick={ingestNow}>Refresh now (ingest + publish)</button>
          <button onClick={refreshPoints}>Reload map points</button>
        </div>

        <hr />

        <label>
          Choropleth metric:&nbsp;
          <select value={metric} onChange={e => setMetric(e.target.value)}>
            <option value="temperature">Temperature</option>
            <option value="pressure">Pressure</option>
            <option value="relativeHumidity">Relative Humidity</option>
          </select>
        </label>
        <div style={{ marginTop:8 }}>
          <button onClick={loadChoropleth}>Load choropleth (IDW)</button>
          <button onClick={() => setChoropleth(null)} style={{ marginLeft:8 }}>Clear</button>
        </div>

        <hr />

        <h3>Dashboard (last 24h)</h3>
        {!selectedStation ? (
          <p style={{ color:"#777" }}>Select a station marker on the map to load its series.</p>
        ) : (
          <>
            <div style={{ fontSize:14, color:"#444" }}>
              <b>Station:</b> {selectedStation}
            </div>
            <div style={{ marginTop:8 }}>
              <LineChart width={340} height={240} data={series}>
                <XAxis dataKey="t" tickFormatter={t => new Date(t).getHours()} />
                <YAxis />
                <Tooltip labelFormatter={fmt} />
                <Legend />
                <Line type="monotone" dataKey="temperature" dot={false} />
                <Line type="monotone" dataKey="pressure" dot={false} />
                <Line type="monotone" dataKey="relativeHumidity" dot={false} />
              </LineChart>
            </div>
          </>
        )}

        <hr />
        <small style={{ color:"#666" }}>
          Tip: apri RabbitMQ UI (15672) e controlla la coda <code>meteo.realtime</code>.
        </small>
      </div>

      <div style={{ height:"100vh" }}>
        <MapContainer center={center} zoom={10} style={{ height:"100vh", width:"100%" }}>
          <TileLayer
            attribution='&copy; OpenStreetMap contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {points.map((p, idx) => {
            const pos = [p.lat, p.lon];
            const label = p.stationId || p.stationName || `station-${idx}`;
            return (
              <Marker key={idx} position={pos} eventHandlers={{
                click: async () => {
                  setSelectedStation(p.stationId || p.stationName || null);
                  if (p.stationId) await loadSeries(p.stationId);
                }
              }}>
                <Popup>
                  <div style={{ minWidth:220 }}>
                    <div><b>{label}</b></div>
                    <div>{p.city || ""}</div>
                    <div style={{ marginTop:6 }}><b>Datetime:</b> {fmt(p.observedAt)}</div>
                    <div><b>Temperature:</b> {p.temperature ?? "—"}</div>
                    <div><b>RH:</b> {p.relativeHumidity ?? "—"}</div>
                    <div><b>Pressure:</b> {p.pressure ?? "—"}</div>
                  </div>
                </Popup>
              </Marker>
            );
          })}

          {choroplethPts.map((c, i) => (
            <CircleMarker
              key={`c-${i}`}
              center={[c.lat, c.lon]}
              radius={3}
              pathOptions={{ opacity: 0.5, fillOpacity: 0.35 }}
            />
          ))}
        </MapContainer>
      </div>
    </div>
  );
}
