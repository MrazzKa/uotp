import uuid
from datetime import datetime
from decimal import Decimal

from geoalchemy2 import Geometry
from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TenantScopedMixin


class IssueNumberCounter(Base):
    __tablename__ = "issue_number_counters"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    next_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class Issue(TenantScopedMixin, Base):
    __tablename__ = "issues"

    public_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    primary_category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"))
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    qualified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    qualified_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    address: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    geometry: Mapped[object | None] = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    district_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("districts.id"))
    object_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    department_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("departments.id"))
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reaction_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    inspection_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_overdue: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sla_paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    on_site_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    parent_issue_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("issues.id"))
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reopen_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024))

    category = relationship("Category", lazy="selectin")
    district = relationship("District", lazy="selectin")
    department = relationship("Department", lazy="selectin")
    created_by = relationship("User", foreign_keys=[created_by_id], lazy="selectin")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id], lazy="selectin")
    attachments = relationship("IssueAttachment", back_populates="issue", lazy="selectin")
    comments = relationship("IssueComment", back_populates="issue", lazy="selectin")
    history = relationship("IssueHistory", back_populates="issue", lazy="selectin")
    assignees = relationship("IssueAssignee", back_populates="issue", lazy="selectin")


class IssueHistory(TenantScopedMixin, Base):
    __tablename__ = "issue_history"

    issue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("issues.id"), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(50))
    to_status: Mapped[str | None] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    issue = relationship("Issue", back_populates="history")
    actor = relationship("User", lazy="selectin")


class IssueAttachment(TenantScopedMixin, Base):
    __tablename__ = "issue_attachments"

    issue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("issues.id"), nullable=False)
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    medium_url: Mapped[str | None] = mapped_column(Text)
    attachment_type: Mapped[str] = mapped_column(String(32), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    perceptual_hash: Mapped[str | None] = mapped_column(String(128))
    antifraud_flags: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    issue = relationship("Issue", back_populates="attachments")
    uploaded_by = relationship("User", lazy="selectin")
    exif = relationship("ExifData", back_populates="attachment", uselist=False)


class ExifData(TenantScopedMixin, Base):
    __tablename__ = "exif_data"

    attachment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("issue_attachments.id"), nullable=False, unique=True
    )
    raw_exif: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    attachment = relationship("IssueAttachment", back_populates="exif")


class IssueComment(TenantScopedMixin, Base):
    __tablename__ = "issue_comments"

    issue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("issues.id"), nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="ru", nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    issue = relationship("Issue", back_populates="comments")
    author = relationship("User", lazy="selectin")


class IssueAssignee(TenantScopedMixin, Base):
    __tablename__ = "issue_assignees"

    issue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("issues.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    issue = relationship("Issue", back_populates="assignees")
    user = relationship("User", lazy="selectin")
