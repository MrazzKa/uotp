from typing import AsyncIterator

from redis.asyncio import Redis

from app.config import settings


async def get_redis() -> AsyncIterator[Redis]:
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()
