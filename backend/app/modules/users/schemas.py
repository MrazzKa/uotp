from uuid import UUID

from pydantic import BaseModel

from app.modules.roles.schemas import RoleRead
from app.modules.tenants.schemas import TenantRead


class UserRead(BaseModel):
    id: UUID
    full_name: str
    phone: str | None
    email: str | None
    language: str
    position_title: str | None = None
    role: RoleRead
    tenant: TenantRead

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    full_name: str
    email: str
    password: str = "demo123"
    role_id: UUID
    position_title: str | None = None
    sphere_id: UUID | None = None
    department_id: UUID | None = None
    controls_all_spheres: bool = False
    language: str = "ru"


class UserUpdate(BaseModel):
    full_name: str | None = None
    role_id: UUID | None = None
    position_title: str | None = None
    sphere_id: UUID | None = None
    department_id: UUID | None = None
    controls_all_spheres: bool | None = None
    is_active: bool | None = None
