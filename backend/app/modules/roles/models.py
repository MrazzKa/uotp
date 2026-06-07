from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TenantScopedMixin


class Role(TenantScopedMixin, Base):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_roles_tenant_code"),)

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    name_kk: Mapped[str] = mapped_column(String(255), nullable=False)
    permissions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    tenant = relationship("Tenant", back_populates="roles", foreign_keys="Role.tenant_id")
    users = relationship("User", back_populates="role")
