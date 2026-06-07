"""foundation

Revision ID: 0001_foundation
Revises:
Create Date: 2026-06-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_foundation"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def base_columns() -> list[sa.Column]:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "tenants",
        *base_columns(),
        sa.Column("code", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name_ru", sa.String(length=255), nullable=False),
        sa.Column("name_kk", sa.String(length=255), nullable=False),
        sa.Column("subdomain", sa.String(length=64), nullable=True, unique=True),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("locale_default", sa.String(length=8), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "roles",
        *base_columns(),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name_ru", sa.String(length=255), nullable=False),
        sa.Column("name_kk", sa.String(length=255), nullable=False),
        sa.Column("permissions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("tenant_id", "code", name="uq_roles_tenant_code"),
    )
    op.create_table(
        "users",
        *base_columns(),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("district_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("totp_secret", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_phone", "users", ["phone"], unique=True)
    # RLS foundation note: tenant policies will be enabled in a later domain migration.


def downgrade() -> None:
    op.drop_index("ix_users_phone", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("roles")
    op.drop_table("tenants")
