from uuid import UUID

from pydantic import BaseModel


class TenantRead(BaseModel):
    id: UUID
    code: str
    name_ru: str
    name_kk: str
    timezone: str
    locale_default: str

    model_config = {"from_attributes": True}
