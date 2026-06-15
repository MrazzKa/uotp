from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: UUID
    actor_id: UUID | None
    action: str
    entity_type: str
    entity_id: UUID | None
    ip_address: str | None
    context: dict
    created_at: datetime

    model_config = {"from_attributes": True}
