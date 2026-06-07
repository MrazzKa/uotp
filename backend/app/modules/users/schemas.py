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
    role: RoleRead
    tenant: TenantRead

    model_config = {"from_attributes": True}
