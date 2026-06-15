from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class IssueCreate(BaseModel):
    source: str = "portal"
    title: str = Field(min_length=3, max_length=500)
    description: str = Field(min_length=3)
    primary_category_id: UUID | None = None
    priority: str = "MEDIUM"
    address: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    district_id: UUID | None = None
    department_id: UUID | None = None
    assigned_to_id: UUID | None = None
    tags: list[str] = Field(default_factory=list)


class IssueUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=500)
    description: str | None = Field(default=None, min_length=3)
    priority: str | None = None
    address: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    district_id: UUID | None = None
    primary_category_id: UUID | None = None
    department_id: UUID | None = None


class IssueQualify(BaseModel):
    category_id: UUID | None = None
    priority: str = "MEDIUM"
    department_id: UUID | None = None


class IssueAssign(BaseModel):
    assigned_to_id: UUID
    department_id: UUID | None = None


class IssueTransition(BaseModel):
    status: str
    payload: dict = Field(default_factory=dict)


class IssueCommentCreate(BaseModel):
    content: str = Field(min_length=1)
    language: str = "ru"
    is_internal: bool = False


class UserMini(BaseModel):
    id: UUID
    full_name: str
    email: str | None

    model_config = {"from_attributes": True}


class CatalogMini(BaseModel):
    id: UUID
    name_ru: str
    name_kk: str

    model_config = {"from_attributes": True}


class IssueAttachmentRead(BaseModel):
    id: UUID
    file_url: str
    thumbnail_url: str | None
    medium_url: str | None
    attachment_type: str
    mime_type: str
    size_bytes: int
    taken_at: datetime | None
    created_at: datetime
    # Note: geo (latitude/longitude), perceptual_hash and raw EXIF are intentionally
    # excluded from normal responses (ПДн / antifraud isolation — SEC-09).

    model_config = {"from_attributes": True}


class IssueHistoryRead(BaseModel):
    id: UUID
    action: str
    from_status: str | None
    to_status: str | None
    payload: dict
    actor: UserMini | None
    created_at: datetime

    model_config = {"from_attributes": True}


class IssueCommentRead(BaseModel):
    id: UUID
    author: UserMini
    content: str
    language: str
    is_internal: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class IssueListItem(BaseModel):
    id: UUID
    public_number: str
    title: str
    source: str
    status: str
    priority: str
    category: CatalogMini | None
    district: CatalogMini | None
    department: CatalogMini | None
    assigned_to: UserMini | None
    created_at: datetime
    reaction_due_at: datetime | None
    sla_due_at: datetime | None
    inspection_due_at: datetime | None
    is_overdue: bool
    sla_paused_at: datetime | None

    model_config = {"from_attributes": True}


class IssueListResponse(BaseModel):
    items: list[IssueListItem]
    next_cursor: str | None


class IssueDetail(IssueListItem):
    description: str
    address: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    created_by: UserMini
    accepted_at: datetime | None
    on_site_at: datetime | None
    completed_at: datetime | None
    closed_at: datetime | None
    reopen_count: int
    attachments: list[IssueAttachmentRead]
    comments: list[IssueCommentRead]
    history: list[IssueHistoryRead]
