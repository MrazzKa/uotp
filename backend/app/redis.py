from typing import AsyncIterator

from redis.asyncio import Redis

from app.config import settings

_client: Redis | None = None


def get_redis_client() -> Redis:
    """Process-wide Redis client (connection-pooled by redis-py)."""
    global _client
    if _client is None:
        _client = Redis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def get_redis() -> AsyncIterator[Redis]:
    yield get_redis_client()
