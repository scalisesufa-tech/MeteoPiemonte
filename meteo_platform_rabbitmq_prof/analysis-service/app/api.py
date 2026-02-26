import asyncio
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from .broker import consume_forever, latest_points
from .interpolation import idw_grid, grid_to_geojson

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
    asyncio.create_task(consume_forever())

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/latest")
def latest(metric: str = Query("temperature", pattern="^(temperature|pressure|relativeHumidity)$")):
    return {"points": latest_points(metric)}

@app.get("/choropleth")
def choropleth(
    metric: str = Query("temperature", pattern="^(temperature|pressure|relativeHumidity)$"),
    minLat: float = 44.7,
    maxLat: float = 45.3,
    minLon: float = 7.2,
    maxLon: float = 7.9,
    nx: int = 45,
    ny: int = 45
):
    pts = latest_points(metric)
    grid = idw_grid(pts, {"minLat":minLat,"maxLat":maxLat,"minLon":minLon,"maxLon":maxLon}, nx=nx, ny=ny)
    if grid is None:
        return {"type":"FeatureCollection","features":[]}
    glats, glons, Z = grid
    return grid_to_geojson(glats, glons, Z)
