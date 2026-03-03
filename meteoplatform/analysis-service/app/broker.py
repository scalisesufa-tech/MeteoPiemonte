import os
import asyncio
import json
import logging
from typing import Dict, Any, List

import aio_pika

from .models import RealtimeEvent

logger = logging.getLogger("broker")

# Default points to the docker-compose service name ("rabbitmq").
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
QUEUE_NAME = os.getenv("QUEUE_NAME", "meteo.realtime")

# Latest observation per station.
LATEST: Dict[str, RealtimeEvent] = {}


async def consume_forever():
    """Continuously consume realtime events from RabbitMQ and keep an in-memory latest map."""
    while True:
        try:
            logger.info("Connecting to RabbitMQ at %s (queue=%s)", RABBITMQ_URL, QUEUE_NAME)
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            async with connection:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=200)

                # Declare the queue so the system works even on a fresh broker.
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
                                # Keep the consumer alive but log the bad payload.
                                logger.warning("Skipping bad message: %s", e)

        except Exception as e:
            logger.error("RabbitMQ consumer error: %s", e)
            await asyncio.sleep(2)


def latest_points(metric: str) -> List[Dict[str, Any]]:
    pts: List[Dict[str, Any]] = []
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
