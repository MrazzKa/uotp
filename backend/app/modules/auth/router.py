from typing import Annotated

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.modules.auth.schemas import LoginRequest, LogoutRequest, MeResponse, RefreshRequest, TokenPair
from app.modules.auth.service import authenticate, refresh_access_token, revoke_refresh_token
from app.modules.users.models import User
from app.redis import get_redis

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, session: Annotated[AsyncSession, Depends(get_session)]):
    return await authenticate(session, payload.login, payload.password)


@router.post("/refresh", response_model=TokenPair)
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
async def logout(payload: LogoutRequest, redis: Annotated[Redis, Depends(get_redis)]):
    await revoke_refresh_token(redis, payload.refresh_token)
    return {"ok": True}
