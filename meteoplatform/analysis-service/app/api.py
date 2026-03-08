import asyncio
import logging
from typing import List
from pydantic import BaseModel

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import numpy as np

from .broker import consume_forever, latest_points
from .interpolation import idw_grid, grid_to_geojson

# Ensure our broker logs show up in container logs.
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="analysis-service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    # Run the RabbitMQ consumer in the background.
    asyncio.create_task(consume_forever())

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logging.error(f"Validation Error: {exc.errors()} Body: {exc.body}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/latest")
def latest(metric: str = Query("temperature", pattern="^(temperature|pressure|relativeHumidity)$")):
    return {"points": latest_points(metric)}


@app.get("/stats")
def stats(metric: str = Query("temperature", pattern="^(temperature|pressure|relativeHumidity)$")):
    pts = latest_points(metric)
    if not pts:
        return {"min": None, "max": None, "avg": None, "count": 0}
    vals = [p["value"] for p in pts if p["value"] is not None]
    if not vals:
        return {"min": None, "max": None, "avg": None, "count": 0}
    return {
        "min": float(min(vals)),
        "max": float(max(vals)),
        "avg": float(sum(vals) / len(vals)),
        "count": len(vals)
    }


@app.get("/choropleth")
def choropleth(
    metric: str = Query("temperature", pattern="^(temperature|pressure|relativeHumidity)$"),
    minLat: float = 44.7,
    maxLat: float = 45.3,
    minLon: float = 7.2,
    maxLon: float = 7.9,
    nx: int = 45,
    ny: int = 45,
):
    pts = latest_points(metric)
    grid = idw_grid(
        pts,
        {"minLat": minLat, "maxLat": maxLat, "minLon": minLon, "maxLon": maxLon},
        nx=nx,
        ny=ny,
    )
    if grid is None:
        return {"type": "FeatureCollection", "features": []}
    glats, glons, Z = grid
    return grid_to_geojson(glats, glons, Z)


class ForecastRequest(BaseModel):
    lat: float
    lon: float
    metric: str
    hoursAhead: int = 24

OM_METRIC_MAP = {
    "temperature": "temperature_2m",
    "pressure": "surface_pressure",
    "relativeHumidity": "relative_humidity_2m"
}

import httpx
from datetime import datetime, timezone

@app.post("/forecast")
async def forecast(req: ForecastRequest):
    om_metric = OM_METRIC_MAP.get(req.metric, "temperature_2m")
    url = f"https://api.open-meteo.com/v1/forecast?latitude={req.lat}&longitude={req.lon}&hourly={om_metric}&forecast_days=2"
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, timeout=10.0)
            res.raise_for_status()
            data = res.json()
            
            times = data["hourly"]["time"]
            vals = data["hourly"][om_metric]
            
            # Find current index
            now = datetime.now(timezone.utc)
            current_iso = now.strftime("%Y-%m-%dT%H:00")
            
            try:
                # Find closest index or just first element matching today hour
                idx = next(i for i, t in enumerate(times) if t >= current_iso)
            except StopIteration:
                idx = 0
            
            forecast_pts = []
            for i in range(1, req.hoursAhead + 1):
                if idx + i < len(times):
                    # Open Meteo time is usually in local/UTC depending on request, by default UTC.
                    # Convert to milliseconds for chart
                    dt = datetime.fromisoformat(times[idx + i])
                    t_ms = dt.replace(tzinfo=timezone.utc).timestamp() * 1000
                    forecast_pts.append({"t": t_ms, "value": vals[idx + i]})
                    
            return {"forecast": forecast_pts}
        except Exception as e:
            logging.error(f"Open-Meteo API error: {e}")
            return {"forecast": []}


@app.get("/choropleth/forecast")
async def choropleth_forecast(
    metric: str = Query("temperature", pattern="^(temperature|pressure|relativeHumidity)$"),
    hoursAhead: int = Query(3, ge=1, le=24),
    minLat: float = 44.7,
    maxLat: float = 45.3,
    minLon: float = 7.2,
    maxLon: float = 7.9,
    nx: int = 40,
    ny: int = 40,
):
    # To avoid rate limiting, we generate a 5x5 geographical bounding box grid 
    # and call Open-Meteo for these 25 points. Then we IDW interpolate these 25 points into the 40x40 map grid!
    grid_lat = np.linspace(minLat, maxLat, 5)
    grid_lon = np.linspace(minLon, maxLon, 5)
    
    lats = []
    lons = []
    for glat in grid_lat:
        for glon in grid_lon:
            lats.append(round(glat, 4))
            lons.append(round(glon, 4))
            
    lat_str = ",".join(map(str, lats))
    lon_str = ",".join(map(str, lons))
    
    om_metric = OM_METRIC_MAP.get(metric, "temperature_2m")
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat_str}&longitude={lon_str}&hourly={om_metric}&forecast_days=2"
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, timeout=15.0)
            res.raise_for_status()
            data = res.json()
            
            forecasted_pts = []
            if isinstance(data, list):
                # Multiple locations response
                for i, loc_data in enumerate(data):
                    times = loc_data["hourly"]["time"]
                    vals = loc_data["hourly"][om_metric]
                    
                    now = datetime.now(timezone.utc)
                    current_iso = now.strftime("%Y-%m-%dT%H:00")
                    try:
                        idx = next(k for k, t in enumerate(times) if t >= current_iso)
                    except StopIteration:
                        idx = 0
                        
                    future_idx = idx + hoursAhead
                    val = vals[future_idx] if future_idx < len(vals) else vals[-1]
                    
                    forecasted_pts.append({
                        "lat": loc_data["latitude"],
                        "lon": loc_data["longitude"],
                        "value": val
                    })
            else:
                # Fallback if only 1 location returned (unlikely) or if it's an error dict
                logging.warning(f"Open-Meteo returned dict instead of list. Data keys: {list(data.keys()) if isinstance(data, dict) else 'unknown'}")
                if isinstance(data, dict) and "error" in data:
                    logging.error(f"Open-Meteo API Error: {data.get('reason')}")
                
            grid = idw_grid(
                forecasted_pts,
                {"minLat": minLat, "maxLat": maxLat, "minLon": minLon, "maxLon": maxLon},
                nx=nx,
                ny=ny,
            )
            if grid is None:
                return {"type": "FeatureCollection", "features": []}
            glats, glons, Z = grid
            return grid_to_geojson(glats, glons, Z)
            
        except Exception as e:
            logging.error(f"Open-Meteo grid error: {e}")
            return {"type": "FeatureCollection", "features": []}
