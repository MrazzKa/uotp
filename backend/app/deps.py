from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.users.models import User
from app.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    user = await session.get(User, payload.get("sub"))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return user


def require_roles(*roles: str) -> Callable:
    async def dependency(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role is None or current_user.role.code not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return current_user

    return dependency


async def tenant_filter(request: Request, current_user: Annotated[User, Depends(get_current_user)]) -> User:
    request.state.tenant_id = current_user.tenant_id
    return current_user
