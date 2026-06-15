from uuid import UUID

from pydantic import BaseModel, Field


class SlaRuleRead(BaseModel):
    id: UUID
    category_id: UUID | None
    priority: str | None
    reaction_minutes: int
    execution_minutes: int
    inspection_minutes: int
    is_24_7: bool
    is_active: bool

    model_config = {"from_attributes": True}


class SlaRuleUpsert(BaseModel):
    category_id: UUID | None = None
    priority: str | None = None
    reaction_minutes: int = Field(gt=0)
    execution_minutes: int = Field(gt=0)
    inspection_minutes: int = Field(gt=0)
    is_24_7: bool = True
    is_active: bool = True
