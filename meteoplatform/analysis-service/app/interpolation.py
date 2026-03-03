from typing import List, Dict, Any
import numpy as np

def idw_grid(points: List[Dict[str, Any]], bbox: Dict[str, float], nx: int = 40, ny: int = 40, power: float = 2.0):
    if not points:
        return None

    lats = np.array([p["lat"] for p in points], dtype=float)
    lons = np.array([p["lon"] for p in points], dtype=float)
    vals = np.array([p["value"] for p in points], dtype=float)

    grid_lats = np.linspace(bbox["minLat"], bbox["maxLat"], ny)
    grid_lons = np.linspace(bbox["minLon"], bbox["maxLon"], nx)

    Z = np.zeros((ny, nx), dtype=float)

    for iy, la in enumerate(grid_lats):
        for ix, lo in enumerate(grid_lons):
            d = np.sqrt((lats - la)**2 + (lons - lo)**2)
            d = np.maximum(d, 1e-6)
            w = 1.0 / (d**power)
            Z[iy, ix] = float(np.sum(w * vals) / np.sum(w))

    return grid_lats, grid_lons, Z

def grid_to_geojson(grid_lats, grid_lons, Z):
    features = []
    for iy, la in enumerate(grid_lats):
        for ix, lo in enumerate(grid_lons):
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(lo), float(la)]},
                "properties": {"value": float(Z[iy, ix])}
            })
    return {"type": "FeatureCollection", "features": features}
