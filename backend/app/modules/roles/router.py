from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.modules.roles.models import Role
from app.modules.roles.schemas import RoleRead
from app.modules.users.models import User

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[RoleRead])
async def list_roles(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(
        select(Role).where(Role.tenant_id == current_user.tenant_id).order_by(Role.name_ru)
    )
    return result.scalars().all()
