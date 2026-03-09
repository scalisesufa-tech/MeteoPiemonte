import os
import asyncio
import json
import logging
from typing import Dict, Any, List

import aio_pika
import httpx

from .models import RealtimeEvent

logger = logging.getLogger("broker")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
QUEUE_NAME = os.getenv("QUEUE_NAME", "meteo.realtime")
LATEST: Dict[str, RealtimeEvent] = {}


async def consume_forever():
    while True:
        try:
            logger.info("Connecting to RabbitMQ at %s (queue=%s)", RABBITMQ_URL, QUEUE_NAME)
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            async with connection:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=200)
                queue = await channel.declare_queue(QUEUE_NAME, durable=True)
                logger.info("Consuming from queue '%s'", QUEUE_NAME)
                async with queue.iterator() as qiterator:
                    async for message in qiterator:
                        async with message.process(requeue=False):
                            try:
                                payload = json.loads(message.body.decode("utf-8"))
                                ev = RealtimeEvent(**payload)
                                key = ev.stationId or ev.stationName or "unknown"
                                LATEST[key] = ev
                            except Exception as e:
                                logger.warning("Skipping bad message: %s", e)
        except Exception as e:
            logger.error("RabbitMQ consumer error: %s", e)
            await asyncio.sleep(2)


def latest_points(metric: str) -> List[Dict[str, Any]]:
    pts: List[Dict[str, Any]] = []
    for _, ev in LATEST.items():
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
        pts.append({
            "stationId": ev.stationId,
            "stationName": ev.stationName,
            "lat": ev.lat,
            "lon": ev.lon,
            "value": value,
            "observedAt": ev.observedAt.isoformat() if hasattr(ev.observedAt, 'isoformat') else ev.observedAt,
        })
    return pts


async def latest_points_with_fallback(metric: str, core_api_base: str) -> List[Dict[str, Any]]:
    pts = latest_points(metric)
    if pts:
        return pts

    url = f"{core_api_base}/api/geo/latest?minutes=180&limit=2000"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(url)
            res.raise_for_status()
            data = res.json()
            out = []
            for o in data if isinstance(data, list) else []:
                value = o.get(metric)
                if value is None:
                    continue
                out.append({
                    "stationId": o.get("stationId"),
                    "stationName": o.get("stationName"),
                    "lat": o.get("lat"),
                    "lon": o.get("lon"),
                    "value": value,
                    "observedAt": o.get("observedAt"),
                })
            return out
    except Exception as exc:
        logger.warning("Core API fallback failed: %s", exc)
        return []
