from uuid import UUID

from pydantic import BaseModel


class RoleRead(BaseModel):
    id: UUID
    code: str
    name_ru: str
    name_kk: str
    permissions: dict

    model_config = {"from_attributes": True}
