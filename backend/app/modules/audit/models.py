import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, TenantScopedMixin


class AuditLog(TenantScopedMixin, Base):
    """Append-only journal of user actions and access to personal data.

    UPDATE/DELETE are blocked at the database level by triggers (see migration 0006).
    ``context`` is the JSONB payload column (``metadata`` is reserved by SQLAlchemy).
    """

    __tablename__ = "audit_log"

    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    context: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
