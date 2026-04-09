import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import httpx
import numpy as np
from fastapi import FastAPI, Query
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .broker import consume_forever, latest_points, latest_points_with_fallback
from .interpolation import idw_grid, grid_to_geojson

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("analysis-service")

CORE_API_BASE = os.getenv("CORE_API_BASE", "http://meteo-core:8080")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
FORECAST_CACHE_TTL_SECONDS = int(os.getenv("FORECAST_CACHE_TTL_SECONDS", "1800"))
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))

app = FastAPI(title="analysis-service", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = None
try:
    import redis.asyncio as redis
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except Exception as exc:  # pragma: no cover
    logger.warning("Redis disabled: %s", exc)

OM_METRIC_MAP = {
    "temperature": "temperature_2m",
    "pressure": "surface_pressure",
    "relativeHumidity": "relative_humidity_2m"
}
METNO_METRIC_MAP = {
    "temperature": "air_temperature",
    "pressure": "air_pressure_at_sea_level",
    "relativeHumidity": "relative_humidity"
}


@app.on_event("startup")
async def startup():
    asyncio.create_task(consume_forever())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error("Validation Error: %s Body: %s", exc.errors(), exc.body)
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.get("/health")
def health():
    return {"status": "ok", "redis": redis_client is not None}


@app.get("/latest")
async def latest(metric: str = Query("temperature", pattern="^(temperature|pressure|relativeHumidity)$")):
    return {"points": await latest_points_with_fallback(metric, CORE_API_BASE)}


@app.get("/stats")
async def stats(metric: str = Query("temperature", pattern="^(temperature|pressure|relativeHumidity)$")):
    pts = await latest_points_with_fallback(metric, CORE_API_BASE)
    if not pts:
        return {"min": None, "max": None, "avg": None, "count": 0}
    vals = [p["value"] for p in pts if p.get("value") is not None]
    if not vals:
        return {"min": None, "max": None, "avg": None, "count": 0}
    return {"min": float(min(vals)), "max": float(max(vals)), "avg": float(sum(vals) / len(vals)), "count": len(vals)}


@app.get("/choropleth")
async def choropleth(metric: str = Query("temperature", pattern="^(temperature|pressure|relativeHumidity)$"),
    minLat: float = 44.7, maxLat: float = 45.3, minLon: float = 7.2, maxLon: float = 7.9, nx: int = 45, ny: int = 45):
    pts = await latest_points_with_fallback(metric, CORE_API_BASE)
    grid = idw_grid(pts, {"minLat": minLat, "maxLat": maxLat, "minLon": minLon, "maxLon": maxLon}, nx=nx, ny=ny)
    if grid is None:
        return {"type": "FeatureCollection", "features": []}
    glats, glons, z = grid
    return grid_to_geojson(glats, glons, z)


class ForecastRequest(BaseModel):
    lat: float
    lon: float
    metric: str
    hoursAhead: int = 24


async def _cache_get(key: str) -> Optional[dict]:
    if redis_client is None:
        return None
    try:
        val = await redis_client.get(key)
        return json.loads(val) if val else None
    except Exception as exc:
        logger.warning("Redis read failed: %s", exc)
        return None


async def _cache_set(key: str, payload: dict):
    if redis_client is None:
        return
    try:
        await redis_client.setex(key, FORECAST_CACHE_TTL_SECONDS, json.dumps(payload))
    except Exception as exc:
        logger.warning("Redis write failed: %s", exc)


async def _openmeteo_forecast(lat: float, lon: float, metric: str, hours_ahead: int) -> Optional[dict]:
    om_metric = OM_METRIC_MAP.get(metric, "temperature_2m")
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly={om_metric}&forecast_days=2"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        res = await client.get(url)
        res.raise_for_status()
        data = res.json()
        times = data["hourly"]["time"]
        vals = data["hourly"][om_metric]
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00")
        idx = next((i for i, t in enumerate(times) if t >= now), 0)
        forecast_pts = []
        for i in range(1, hours_ahead + 1):
            pos = idx + i
            if pos < len(times):
                dt = datetime.fromisoformat(times[pos])
                t_ms = dt.replace(tzinfo=timezone.utc).timestamp() * 1000
                forecast_pts.append({"t": t_ms, "value": vals[pos]})
        return {"forecast": forecast_pts, "provider": "open-meteo"}


async def _metno_forecast(lat: float, lon: float, metric: str, hours_ahead: int) -> Optional[dict]:
    metric_name = METNO_METRIC_MAP.get(metric, "air_temperature")
    headers = {"User-Agent": "MeteoPlatform/1.0 student-project"}
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat}&lon={lon}"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS, headers=headers) as client:
        res = await client.get(url)
        res.raise_for_status()
        data = res.json()
        series = data.get("properties", {}).get("timeseries", [])
        forecast_pts = []
        now = datetime.now(timezone.utc)
        for entry in series:
            ts = datetime.fromisoformat(entry["time"].replace("Z", "+00:00"))
            if ts <= now:
                continue
            details = entry.get("data", {}).get("instant", {}).get("details", {})
            if metric_name in details:
                forecast_pts.append({"t": ts.timestamp() * 1000, "value": details[metric_name]})
            if len(forecast_pts) >= hours_ahead:
                break
        return {"forecast": forecast_pts, "provider": "met-no"}


@app.post("/forecast")
async def forecast(req: ForecastRequest):
    cache_key = f"forecast:{req.metric}:{req.lat:.4f}:{req.lon:.4f}:{req.hoursAhead}"
    cached = await _cache_get(cache_key)
    if cached:
        cached["cached"] = True
        return cached

    for provider in (_openmeteo_forecast, _metno_forecast):
        try:
            payload = await provider(req.lat, req.lon, req.metric, req.hoursAhead)
            if payload and payload.get("forecast"):
                await _cache_set(cache_key, payload)
                payload["cached"] = False
                return payload
        except Exception as exc:
            logger.warning("Forecast provider %s failed: %s", provider.__name__, exc)

    return cached or {"forecast": [], "provider": "none", "cached": False}


@app.get("/choropleth/forecast")
async def choropleth_forecast(metric: str = Query("temperature", pattern="^(temperature|pressure|relativeHumidity)$"),
    hoursAhead: int = Query(3, ge=1, le=24), minLat: float = 44.7, maxLat: float = 45.3, minLon: float = 7.2, maxLon: float = 7.9, nx: int = 40, ny: int = 40):
    grid_lat = np.linspace(minLat, maxLat, 5)
    grid_lon = np.linspace(minLon, maxLon, 5)
    forecasted_pts = []
    for glat in grid_lat:
        for glon in grid_lon:
            payload = await forecast(ForecastRequest(lat=round(glat,4), lon=round(glon,4), metric=metric, hoursAhead=hoursAhead))
            if payload.get("forecast"):
                forecasted_pts.append({"lat": round(glat,4), "lon": round(glon,4), "value": payload["forecast"][-1]["value"]})

    grid = idw_grid(forecasted_pts, {"minLat": minLat, "maxLat": maxLat, "minLon": minLon, "maxLon": maxLon}, nx=nx, ny=ny)
    if grid is None:
        return {"type": "FeatureCollection", "features": []}
    glats, glons, z = grid
    return grid_to_geojson(glats, glons, z)
