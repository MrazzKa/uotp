from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TenantScopedMixin


class User(TenantScopedMixin, Base):
    __tablename__ = "users"

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    department_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    district_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="ru", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    totp_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # v3: штатное расписание и зона контроля по сфере
    position_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sphere_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    controls_all_spheres: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    tenant = relationship("Tenant", back_populates="users", foreign_keys="User.tenant_id", lazy="selectin")
    role = relationship("Role", back_populates="users", lazy="selectin")
    department = relationship(
        "Department",
        primaryjoin="User.department_id == Department.id",
        foreign_keys="User.department_id",
        lazy="selectin",
        viewonly=True,
    )

    @property
    def organization(self) -> str | None:
        """Название организации/подразделения исполнителя — куда ушло поручение."""
        return self.department.name_ru if self.department is not None else None
