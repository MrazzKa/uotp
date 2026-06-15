"""sla rules

Revision ID: 0003_sla_rules
Revises: 0002_issues_core
Create Date: 2026-06-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_sla_rules"
down_revision: Union[str, None] = "0002_issues_core"
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
    op.create_table(
        "sla_rules",
        *base_columns(),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id")),
        sa.Column("priority", sa.String(20)),
        sa.Column("reaction_minutes", sa.Integer(), nullable=False),
        sa.Column("execution_minutes", sa.Integer(), nullable=False),
        sa.Column("inspection_minutes", sa.Integer(), nullable=False),
        sa.Column("is_24_7", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("tenant_id", "category_id", "priority", name="uq_sla_rules_scope"),
    )
    op.create_index("ix_sla_rules_tenant_active", "sla_rules", ["tenant_id", "is_active"])

    priorities = [
        ("CRITICAL", 60, 240, 1440),
        ("HIGH", 120, 480, 1440),
        ("MEDIUM", 240, 1440, 1440),
        ("LOW", 480, 2880, 1440),
        (None, 240, 1440, 1440),
    ]
    values = ", ".join(
        f"({'NULL' if priority is None else repr(priority)}, {reaction}, {execution}, {inspection})"
        for priority, reaction, execution, inspection in priorities
    )
    op.execute(
        "INSERT INTO sla_rules (id, tenant_id, priority, reaction_minutes, execution_minutes, inspection_minutes, category_id, is_24_7, is_active) "
        f"SELECT uuid_generate_v4(), tenants.id, v.priority, v.reaction_minutes, v.execution_minutes, v.inspection_minutes, NULL, TRUE, TRUE "
        f"FROM tenants CROSS JOIN (VALUES {values}) AS v(priority, reaction_minutes, execution_minutes, inspection_minutes)"
    )


def downgrade() -> None:
    op.drop_index("ix_sla_rules_tenant_active", table_name="sla_rules")
    op.drop_table("sla_rules")
