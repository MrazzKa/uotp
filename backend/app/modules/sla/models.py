import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TenantScopedMixin


class SlaRule(TenantScopedMixin, Base):
    __tablename__ = "sla_rules"
    __table_args__ = (
        UniqueConstraint("tenant_id", "category_id", "priority", name="uq_sla_rules_scope"),
    )

    category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"))
    priority: Mapped[str | None] = mapped_column(String(20))
    reaction_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    execution_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    inspection_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_24_7: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category = relationship("Category", lazy="selectin")
