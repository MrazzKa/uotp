import jwt
from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.modules.auth.schemas import TokenPair
from app.modules.users.models import User
from app.modules.users.service import get_user_by_login
from app.security import create_token, decode_token, verify_password


def make_token_pair(user: User) -> TokenPair:
    tenant_id = str(user.tenant_id)
    role = user.role.code
    return TokenPair(
        access_token=create_token(
            str(user.id), tenant_id, role, settings.access_token_ttl, "access"
        ),
        refresh_token=create_token(
            str(user.id), tenant_id, role, settings.refresh_token_ttl, "refresh"
        ),
    )


async def authenticate(session: AsyncSession, login: str, password: str) -> TokenPair:
    user = await get_user_by_login(session, login)
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return make_token_pair(user)


async def refresh_access_token(session: AsyncSession, redis: Redis, refresh_token: str) -> TokenPair:
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    if await redis.get(f"blacklist:{payload['jti']}"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")
    user = await session.get(User, payload["sub"])
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return make_token_pair(user)


async def revoke_refresh_token(redis: Redis, refresh_token: str) -> None:
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        return
    if payload.get("type") == "refresh":
        await redis.setex(f"blacklist:{payload['jti']}", settings.refresh_token_ttl, "1")
