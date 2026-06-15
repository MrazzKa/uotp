from uuid import UUID

from pydantic import BaseModel


class DepartmentRead(BaseModel):
    id: UUID
    name_ru: str
    name_kk: str
    type: str
    parent_id: UUID | None
    head_user_id: UUID | None
    contacts: dict

    model_config = {"from_attributes": True}


class DistrictRead(BaseModel):
    id: UUID
    name_ru: str
    name_kk: str
    code: str
    parent_id: UUID | None

    model_config = {"from_attributes": True}


class CategoryRead(BaseModel):
    id: UUID
    code: str
    name_ru: str
    name_kk: str
    parent_id: UUID | None
    default_priority: str
    default_department_id: UUID | None
    icon: str | None
    color: str | None

    model_config = {"from_attributes": True}
