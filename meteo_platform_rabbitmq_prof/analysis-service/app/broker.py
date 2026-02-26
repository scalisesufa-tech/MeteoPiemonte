import os
import asyncio
import json
from typing import Dict, Any, List
import aio_pika
from .models import RealtimeEvent

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
QUEUE_NAME = os.getenv("QUEUE_NAME", "meteo.realtime")

LATEST: Dict[str, RealtimeEvent] = {}

async def consume_forever():
    while True:
        try:
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            async with connection:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=200)
                queue = await channel.declare_queue(QUEUE_NAME, durable=True)

                async with queue.iterator() as qiterator:
                    async for message in qiterator:
                        async with message.process(requeue=False):
                            try:
                                payload = json.loads(message.body.decode("utf-8"))
                                ev = RealtimeEvent(**payload)
                                key = ev.stationId or ev.stationName or "unknown"
                                LATEST[key] = ev
                            except Exception:
                                pass
        except Exception:
            await asyncio.sleep(2)

def latest_points(metric: str) -> List[Dict[str, Any]]:
    pts = []
    for k, ev in LATEST.items():
        if ev.lat is None or ev.lon is None:
            continue
        value = None
        if metric == "temperature":
            value = ev.temperature
        elif metric == "pressure":
            value = ev.pressure
        elif metric == "relativeHumidity":
            value = ev.relativeHumidity
        if value is None:
            continue
        pts.append({"id": k, "lat": ev.lat, "lon": ev.lon, "value": float(value)})
    return pts
