from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.modules.catalog.models import Category, Department, District
from app.modules.catalog.schemas import CategoryRead, DepartmentRead, DistrictRead
from app.modules.users.models import User

router = APIRouter(tags=["catalog"])


@router.get("/categories", response_model=list[CategoryRead])
async def list_categories(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(
        select(Category)
        .where(Category.tenant_id == current_user.tenant_id, Category.deleted_at.is_(None))
        .order_by(Category.parent_id.nullsfirst(), Category.name_ru)
    )
    return result.scalars().all()


@router.get("/departments", response_model=list[DepartmentRead])
async def list_departments(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(
        select(Department)
        .where(Department.tenant_id == current_user.tenant_id, Department.deleted_at.is_(None))
        .order_by(Department.name_ru)
    )
    return result.scalars().all()


@router.get("/districts", response_model=list[DistrictRead])
async def list_districts(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(
        select(District)
        .where(District.tenant_id == current_user.tenant_id, District.deleted_at.is_(None))
        .order_by(District.name_ru)
    )
    return result.scalars().all()
