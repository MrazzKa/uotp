import uuid

from geoalchemy2 import Geometry
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TenantScopedMixin


class Department(TenantScopedMixin, Base):
    __tablename__ = "departments"

    name_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    name_kk: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("departments.id"))
    head_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    contacts: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    parent = relationship("Department", remote_side="Department.id")


class District(TenantScopedMixin, Base):
    __tablename__ = "districts"

    name_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    name_kk: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    geometry: Mapped[object | None] = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("districts.id"))

    parent = relationship("District", remote_side="District.id")


class Category(TenantScopedMixin, Base):
    __tablename__ = "categories"

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    name_kk: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"))
    default_priority: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False)
    default_department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id")
    )
    icon: Mapped[str | None] = mapped_column(String(64))
    color: Mapped[str | None] = mapped_column(String(32))

    parent = relationship("Category", remote_side="Category.id")
    default_department = relationship("Department")


class Sphere(TenantScopedMixin, Base):
    """Сфера (направление работы) — по ней автоматически определяется контролёр."""

    __tablename__ = "spheres"

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    name_kk: Mapped[str] = mapped_column(String(255), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(64))
    color: Mapped[str | None] = mapped_column(String(32))
