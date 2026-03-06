import json
from typing import Any

import redis.asyncio as aioredis

from app.config import settings

redis_client: aioredis.Redis = None  # initialized at startup


async def init_redis() -> None:
    global redis_client
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)


async def close_redis() -> None:
    if redis_client:
        await redis_client.aclose()


async def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    await redis_client.set(key, json.dumps(value), ex=ttl)


async def cache_get(key: str) -> Any | None:
    raw = await redis_client.get(key)
    return json.loads(raw) if raw else None


async def push_live_signal(signal_dict: dict) -> None:
    """Store signal in a capped list for the live signals endpoint."""
    pipe = redis_client.pipeline()
    pipe.lpush("signals:live", json.dumps(signal_dict))
    pipe.ltrim("signals:live", 0, 199)  # keep last 200
    await pipe.execute()


async def publish(channel: str, message: dict) -> None:
    await redis_client.publish(channel, json.dumps(message))


async def get_subscriber() -> aioredis.client.PubSub:
    """Returns a new pub/sub connection."""
    sub_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return sub_client.pubsub()
