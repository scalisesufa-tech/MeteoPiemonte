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
            exact_match = d < 1e-6
            if np.any(exact_match):
                Z[iy, ix] = float(vals[exact_match][0])
            else:
                w = 1.0 / (d**power)
                sum_w = np.sum(w)
                if sum_w == 0:
                    Z[iy, ix] = float(np.mean(vals))
                else:
                    val = float(np.sum(w * vals) / sum_w)
                    if np.isnan(val) or np.isinf(val):
                        val = float(np.mean(vals))
                    Z[iy, ix] = val

    return grid_lats, grid_lons, Z

def grid_to_geojson(grid_lats, grid_lons, Z):
    features = []
    for iy, la in enumerate(grid_lats):
        for ix, lo in enumerate(grid_lons):
            val = float(Z[iy, ix])
            if np.isnan(val) or np.isinf(val):
                continue
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(lo), float(la)]},
                "properties": {"value": val}
            })
    return {"type": "FeatureCollection", "features": features}
