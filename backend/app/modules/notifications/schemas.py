from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationRead(BaseModel):
    id: UUID
    type: str
    title: str
    body: str
    issue_id: UUID | None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationRead]
    next_cursor: str | None


class UnreadCountResponse(BaseModel):
    count: int


class DeviceRegister(BaseModel):
    expo_push_token: str = Field(min_length=8)
    platform: str = Field(min_length=2, max_length=32)


class DeviceUnregister(BaseModel):
    expo_push_token: str = Field(min_length=8)
