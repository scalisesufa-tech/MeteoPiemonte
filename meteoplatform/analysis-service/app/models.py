from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class RealtimeEvent(BaseModel):
    stationId: Optional[str] = None
    stationName: Optional[str] = None
    city: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    observedAt: Optional[datetime] = None
    temperature: Optional[float] = None
    relativeHumidity: Optional[float] = None
    pressure: Optional[float] = None
