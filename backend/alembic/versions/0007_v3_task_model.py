"""v3 task model: spheres, personal control, task fields

Revision ID: 0007_v3_task_model
Revises: 0006_audit_log
Create Date: 2026-07-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0007_v3_task_model"
down_revision: Union[str, None] = "0006_audit_log"
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
        "spheres",
        *base_columns(),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name_ru", sa.String(255), nullable=False),
        sa.Column("name_kk", sa.String(255), nullable=False),
        sa.Column("icon", sa.String(64)),
        sa.Column("color", sa.String(32)),
    )
    op.create_index("ix_spheres_tenant_code", "spheres", ["tenant_id", "code"])

    op.create_table(
        "issue_personal_marks",
        *base_columns(),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("issues.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("importance", sa.String(20), nullable=False, server_default="NORMAL"),
        sa.UniqueConstraint("issue_id", "user_id", name="uq_personal_mark_issue_user"),
    )
    op.create_index("ix_personal_marks_user", "issue_personal_marks", ["user_id"])

    # issues: v3-поля (тип, важность, сфера, контролёр, единый срок)
    op.add_column("issues", sa.Column("task_type", sa.String(20), nullable=False, server_default="TASK"))
    op.add_column("issues", sa.Column("importance", sa.String(20), nullable=False, server_default="NORMAL"))
    op.add_column("issues", sa.Column("sphere_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("spheres.id")))
    op.add_column("issues", sa.Column("controller_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")))
    op.add_column("issues", sa.Column("due_at", sa.DateTime(timezone=True)))

    # роль в задаче: EXECUTOR / CO_EXECUTOR
    op.add_column("issue_assignees", sa.Column("role", sa.String(20), nullable=False, server_default="EXECUTOR"))

    # users: штатное расписание и зона контроля
    op.add_column("users", sa.Column("position_title", sa.String(255)))
    op.add_column("users", sa.Column("sphere_id", postgresql.UUID(as_uuid=True)))
    op.add_column("users", sa.Column("controls_all_spheres", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("users", "controls_all_spheres")
    op.drop_column("users", "sphere_id")
    op.drop_column("users", "position_title")
    op.drop_column("issue_assignees", "role")
    op.drop_column("issues", "due_at")
    op.drop_column("issues", "controller_id")
    op.drop_column("issues", "sphere_id")
    op.drop_column("issues", "importance")
    op.drop_column("issues", "task_type")
    op.drop_index("ix_personal_marks_user", table_name="issue_personal_marks")
    op.drop_table("issue_personal_marks")
    op.drop_index("ix_spheres_tenant_code", table_name="spheres")
    op.drop_table("spheres")
