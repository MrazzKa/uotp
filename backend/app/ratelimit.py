from collections.abc import Callable

from fastapi import HTTPException, Request, status

from app.redis import get_redis_client


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def enforce_rate_limit(scope: str, identifier: str, limit: int, window_seconds: int) -> None:
    """Fixed-window limiter backed by Redis. Fails open if Redis is unavailable."""
    key = f"ratelimit:{scope}:{identifier}"
    try:
        redis = get_redis_client()
        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, window_seconds)
    except Exception:
        # Never block legitimate traffic because the limiter store is down.
        return
    if current > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests, please try again later.",
            headers={"Retry-After": str(window_seconds)},
        )


def rate_limit(scope: str, limit: int, window_seconds: int) -> Callable:
    """FastAPI dependency factory keyed by client IP."""

    async def dependency(request: Request) -> None:
        await enforce_rate_limit(scope, _client_ip(request), limit, window_seconds)

    return dependency
