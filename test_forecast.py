import asyncio
import httpx
from datetime import datetime, timezone
import numpy as np

async def test():
    grid_lat = np.linspace(44.7, 45.3, 5)
    grid_lon = np.linspace(7.2, 7.9, 5)
    lats = [round(la, 4) for la in grid_lat for _ in grid_lon]
    lons = [round(lo, 4) for _ in grid_lat for lo in grid_lon]
    
    # Wait, the list comprehension: 
    # for glat in grid_lat: for glon in grid_lon: 
    # My python: [round(la,4) for la in grid_lat for _ in grid_lon] is wrong in my own test??
    # No, in api.py I did:
    # for glat in grid_lat:
    #     for glon in grid_lon:
    #         lats.append(round(glat, 4))
    #         lons.append(round(glon, 4))
    # That is correct in API.
    
    # Let me just curl the API but capture the traceback that FastAPI swallows if it throws a 500.
    pass

asyncio.run(test())
