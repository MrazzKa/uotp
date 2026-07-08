from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user, require_roles
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserRead, UserUpdate
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
async def list_users(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(
        select(User).where(User.tenant_id == current_user.tenant_id, User.deleted_at.is_(None)).order_by(User.full_name)
    )
    return result.scalars().all()


@router.post("", response_model=UserRead)
async def create_user(
    payload: UserCreate,
    current_user: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    exists = (await session.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(status_code=409, detail="Email уже используется.")
    user = User(
        tenant_id=current_user.tenant_id,
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role_id=payload.role_id,
        language=payload.language,
        position_title=payload.position_title,
        sphere_id=payload.sphere_id,
        department_id=payload.department_id,
        controls_all_spheres=payload.controls_all_spheres,
    )
    session.add(user)
    await session.commit()
    uid = user.id
    session.expunge(user)
    return (await session.execute(select(User).where(User.id == uid))).scalar_one()


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    current_user: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    user = (
        await session.execute(
            select(User).where(User.id == user_id, User.tenant_id == current_user.tenant_id, User.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    await session.commit()
    session.expunge(user)
    return (await session.execute(select(User).where(User.id == user_id))).scalar_one()
