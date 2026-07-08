from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class IssueCreate(BaseModel):
    source: str = "internal"
    task_type: str = "TASK"
    title: str = Field(min_length=3, max_length=500)  # текст поручения (кратко)
    description: str = ""  # полный текст поручения (опционально)
    importance: str = "NORMAL"
    priority: str = "MEDIUM"
    sphere_id: UUID | None = None
    controller_id: UUID | None = None
    executor_ids: list[UUID] = Field(default_factory=list)
    co_executor_ids: list[UUID] = Field(default_factory=list)
    due_at: datetime | None = None
    primary_category_id: UUID | None = None
    address: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    district_id: UUID | None = None
    tags: list[str] = Field(default_factory=list)


class IssueUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=500)
    description: str | None = None
    importance: str | None = None
    priority: str | None = None
    sphere_id: UUID | None = None
    controller_id: UUID | None = None
    due_at: datetime | None = None
    address: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    district_id: UUID | None = None
    primary_category_id: UUID | None = None


class IssueAssign(BaseModel):
    executor_ids: list[UUID] = Field(min_length=1)
    co_executor_ids: list[UUID] = Field(default_factory=list)
    controller_id: UUID | None = None
    due_at: datetime | None = None


class IssueSubmit(BaseModel):
    report: str | None = None


class IssueTransition(BaseModel):
    status: str
    payload: dict = Field(default_factory=dict)


class IssuePersonalControl(BaseModel):
    on: bool = True
    importance: str = "NORMAL"


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
    # Note: geo, perceptual_hash and raw EXIF are excluded from normal responses (ПДн — SEC-09).

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
    task_type: str
    status: str
    priority: str
    importance: str
    category: CatalogMini | None
    sphere: CatalogMini | None
    district: CatalogMini | None
    assigned_to: UserMini | None
    controller: UserMini | None
    created_at: datetime
    due_at: datetime | None
    is_overdue: bool

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
    closed_at: datetime | None
    reopen_count: int
    on_personal_control: bool = False
    attachments: list[IssueAttachmentRead]
    comments: list[IssueCommentRead]
    history: list[IssueHistoryRead]
