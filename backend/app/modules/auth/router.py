from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.deps import get_current_user
from app.modules.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    MeResponse,
    RefreshRequest,
    TokenPair,
    TotpCodeRequest,
    TotpSetupResponse,
    TotpStatusResponse,
)
from app.modules.auth.service import (
    authenticate,
    disable_totp,
    enable_totp,
    logout as logout_service,
    refresh_access_token,
    setup_totp,
)
from app.modules.users.models import User
from app.ratelimit import rate_limit
from app.redis import get_redis

router = APIRouter(prefix="/auth", tags=["auth"])

bearer_scheme = HTTPBearer(auto_error=False)
login_rate_limit = rate_limit("auth-login", settings.login_rate_limit, settings.login_rate_window)


@router.post("/login", response_model=TokenPair, dependencies=[Depends(login_rate_limit)])
async def login(payload: LoginRequest, session: Annotated[AsyncSession, Depends(get_session)]):
    return await authenticate(session, payload.login, payload.password, payload.totp_code)


@router.post("/refresh", response_model=TokenPair, dependencies=[Depends(login_rate_limit)])
async def refresh(
    payload: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    return await refresh_access_token(session, redis, payload.refresh_token)


@router.get("/me", response_model=MeResponse)
async def me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@router.post("/logout")
async def logout(
    payload: LogoutRequest,
    redis: Annotated[Redis, Depends(get_redis)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    access_token = credentials.credentials if credentials else None
    await logout_service(redis, access_token, payload.refresh_token)
    return {"ok": True}


@router.get("/2fa/status", response_model=TotpStatusResponse)
async def totp_status(current_user: Annotated[User, Depends(get_current_user)]):
    return {"enabled": bool(current_user.totp_secret)}


@router.post("/2fa/setup", response_model=TotpSetupResponse)
async def totp_setup(
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    secret, uri = await setup_totp(redis, current_user)
    return {"secret": secret, "otpauth_uri": uri}


@router.post("/2fa/enable", response_model=TotpStatusResponse)
async def totp_enable(
    payload: TotpCodeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    await enable_totp(session, redis, current_user, payload.code)
    return {"enabled": True}


@router.post("/2fa/disable", response_model=TotpStatusResponse)
async def totp_disable(
    payload: TotpCodeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    await disable_totp(session, current_user, payload.code)
    return {"enabled": False}
