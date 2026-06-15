import jwt
from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.modules.auth.schemas import TokenPair
from app.modules.users.models import User
from app.modules.users.service import get_user_by_login
from app.security import (
    create_token,
    decode_token,
    generate_totp_secret,
    totp_provisioning_uri,
    token_remaining_ttl,
    verify_password,
    verify_totp,
)


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


async def authenticate(
    session: AsyncSession, login: str, password: str, totp_code: str | None = None
) -> TokenPair:
    user = await get_user_by_login(session, login)
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if user.totp_secret:
        if not totp_code or not verify_totp(user.totp_secret, totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing 2FA code"
            )
    elif settings.admin_2fa_required and user.role is not None and user.role.code == "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="2FA enrollment required for administrators",
        )
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


async def revoke_token(redis: Redis, token: str) -> None:
    """Add a token's jti to the Redis block-list for its remaining lifetime."""
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        return
    jti = payload.get("jti")
    if not jti:
        return
    ttl = token_remaining_ttl(payload)
    if ttl > 0:
        await redis.setex(f"blacklist:{jti}", ttl, "1")


async def logout(redis: Redis, access_token: str | None, refresh_token: str | None) -> None:
    for token in (access_token, refresh_token):
        if token:
            await revoke_token(redis, token)


def _pending_key(user: User) -> str:
    return f"totp_pending:{user.id}"


async def setup_totp(redis: Redis, user: User) -> tuple[str, str]:
    """Generate a pending secret (held in Redis until confirmed) and return (secret, otpauth_uri).

    The secret is not written to ``user.totp_secret`` until ``enable_totp`` confirms a code,
    so a user is never locked out mid-enrollment.
    """
    secret = generate_totp_secret()
    await redis.setex(_pending_key(user), 600, secret)
    account = user.email or user.phone or str(user.id)
    return secret, totp_provisioning_uri(secret, account)


async def enable_totp(session: AsyncSession, redis: Redis, user: User, code: str) -> None:
    secret = await redis.get(_pending_key(user))
    if not secret or not verify_totp(secret, code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired 2FA code")
    user.totp_secret = secret
    await session.commit()
    await redis.delete(_pending_key(user))


async def disable_totp(session: AsyncSession, user: User, code: str) -> None:
    if not user.totp_secret or not verify_totp(user.totp_secret, code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid 2FA code")
    user.totp_secret = None
    await session.commit()
