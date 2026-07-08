from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user, require_roles
from app.modules.catalog.models import Category, Department, District, Sphere
from app.modules.catalog.schemas import CategoryRead, DepartmentRead, DistrictRead
from app.modules.users.models import User

router = APIRouter(tags=["catalog"])


class SphereRead(BaseModel):
    id: UUID
    code: str
    name_ru: str
    name_kk: str
    icon: str | None = None
    color: str | None = None
    controller_id: UUID | None = None

    model_config = {"from_attributes": True}


class SphereWrite(BaseModel):
    code: str
    name_ru: str
    name_kk: str
    icon: str | None = None
    color: str | None = None
    controller_id: UUID | None = None


class SphereUpdate(BaseModel):
    name_ru: str | None = None
    name_kk: str | None = None
    icon: str | None = None
    color: str | None = None
    controller_id: UUID | None = None


class DepartmentWrite(BaseModel):
    name_ru: str
    name_kk: str
    type: str
    parent_id: UUID | None = None
    head_user_id: UUID | None = None


class DepartmentUpdate(BaseModel):
    name_ru: str | None = None
    name_kk: str | None = None
    type: str | None = None
    parent_id: UUID | None = None
    head_user_id: UUID | None = None


async def _get_owned(session: AsyncSession, model, obj_id: UUID, current_user: User):
    obj = (
        await session.execute(
            select(model).where(model.id == obj_id, model.tenant_id == current_user.tenant_id, model.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=404, detail="Не найдено.")
    return obj


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


@router.post("/departments", response_model=DepartmentRead)
async def create_department(
    payload: DepartmentWrite,
    current_user: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    dept = Department(tenant_id=current_user.tenant_id, contacts={}, **payload.model_dump())
    session.add(dept)
    await session.commit()
    await session.refresh(dept)
    return dept


@router.patch("/departments/{department_id}", response_model=DepartmentRead)
async def update_department(
    department_id: UUID,
    payload: DepartmentUpdate,
    current_user: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    dept = await _get_owned(session, Department, department_id, current_user)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(dept, key, value)
    await session.commit()
    await session.refresh(dept)
    return dept


@router.delete("/departments/{department_id}", status_code=204)
async def delete_department(
    department_id: UUID,
    current_user: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    dept = await _get_owned(session, Department, department_id, current_user)
    dept.deleted_at = datetime.now(UTC)
    await session.commit()


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


@router.get("/spheres", response_model=list[SphereRead])
async def list_spheres(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(
        select(Sphere)
        .where(Sphere.tenant_id == current_user.tenant_id, Sphere.deleted_at.is_(None))
        .order_by(Sphere.name_ru)
    )
    return result.scalars().all()


@router.post("/spheres", response_model=SphereRead)
async def create_sphere(
    payload: SphereWrite,
    current_user: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    sphere = Sphere(tenant_id=current_user.tenant_id, **payload.model_dump())
    session.add(sphere)
    await session.commit()
    await session.refresh(sphere)
    return sphere


@router.patch("/spheres/{sphere_id}", response_model=SphereRead)
async def update_sphere(
    sphere_id: UUID,
    payload: SphereUpdate,
    current_user: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    sphere = await _get_owned(session, Sphere, sphere_id, current_user)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(sphere, key, value)
    await session.commit()
    await session.refresh(sphere)
    return sphere


@router.delete("/spheres/{sphere_id}", status_code=204)
async def delete_sphere(
    sphere_id: UUID,
    current_user: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    sphere = await _get_owned(session, Sphere, sphere_id, current_user)
    sphere.deleted_at = datetime.now(UTC)
    await session.commit()
