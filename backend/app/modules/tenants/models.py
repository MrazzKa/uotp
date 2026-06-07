from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TenantScopedMixin


class Tenant(TenantScopedMixin, Base):
    __tablename__ = "tenants"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    name_kk: Mapped[str] = mapped_column(String(255), nullable=False)
    subdomain: Mapped[str | None] = mapped_column(String(64), unique=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Almaty", nullable=False)
    locale_default: Mapped[str] = mapped_column(String(8), default="ru", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    roles = relationship("Role", back_populates="tenant", foreign_keys="Role.tenant_id", lazy="selectin")
    users = relationship("User", back_populates="tenant", foreign_keys="User.tenant_id", lazy="selectin")
