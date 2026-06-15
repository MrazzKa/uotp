"""issues core

Revision ID: 0002_issues_core
Revises: 0001_foundation
Create Date: 2026-06-11
"""
from typing import Sequence, Union

from alembic import op
from geoalchemy2 import Geometry
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_issues_core"
down_revision: Union[str, None] = "0001_foundation"
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

    op.create_table(
        "departments",
        *base_columns(),
        sa.Column("name_ru", sa.String(255), nullable=False),
        sa.Column("name_kk", sa.String(255), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id")),
        sa.Column("head_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("contacts", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_table(
        "districts",
        *base_columns(),
        sa.Column("name_ru", sa.String(255), nullable=False),
        sa.Column("name_kk", sa.String(255), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("geometry", Geometry("MULTIPOLYGON", srid=4326), nullable=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("districts.id")),
    )
    op.create_table(
        "categories",
        *base_columns(),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name_ru", sa.String(255), nullable=False),
        sa.Column("name_kk", sa.String(255), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id")),
        sa.Column("default_priority", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("default_department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id")),
        sa.Column("icon", sa.String(64)),
        sa.Column("color", sa.String(32)),
    )
    op.create_index("ix_departments_tenant_name", "departments", ["tenant_id", "name_ru"])
    op.create_index("ix_districts_tenant_code", "districts", ["tenant_id", "code"])
    op.create_index("ix_categories_tenant_code", "categories", ["tenant_id", "code"])

    op.create_table(
        "issue_number_counters",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("year", sa.Integer(), primary_key=True),
        sa.Column("next_number", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_table(
        "issues",
        *base_columns(),
        sa.Column("public_number", sa.String(20), nullable=False, unique=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("external_id", sa.String(255)),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("primary_category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id")),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'::text[]")),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True)),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("qualified_at", sa.DateTime(timezone=True)),
        sa.Column("qualified_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("address", sa.Text()),
        sa.Column("latitude", sa.Numeric(10, 7)),
        sa.Column("longitude", sa.Numeric(10, 7)),
        sa.Column("geometry", Geometry("POINT", srid=4326), nullable=True),
        sa.Column("district_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("districts.id")),
        sa.Column("object_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assigned_to_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id")),
        sa.Column("sla_due_at", sa.DateTime(timezone=True)),
        sa.Column("reaction_due_at", sa.DateTime(timezone=True)),
        sa.Column("inspection_due_at", sa.DateTime(timezone=True)),
        sa.Column("is_overdue", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sla_paused_at", sa.DateTime(timezone=True)),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("on_site_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("parent_issue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("issues.id")),
        sa.Column("is_duplicate", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reopen_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding", Vector(1024), nullable=True),
    )
    op.create_index("ix_issues_tenant_status", "issues", ["tenant_id", "status"])
    op.create_index("ix_issues_assigned_to_id", "issues", ["assigned_to_id"])
    op.create_index("ix_issues_is_overdue", "issues", ["is_overdue"])
    op.execute("CREATE INDEX ix_issues_geometry_gist ON issues USING gist (geometry)")
    op.execute(
        "CREATE INDEX ix_issues_search_gin ON issues USING gin "
        "(to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(description, '')))"
    )
    op.execute("CREATE INDEX ix_issues_embedding_hnsw ON issues USING hnsw (embedding vector_l2_ops)")

    op.create_table(
        "issue_history",
        *base_columns(),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("issues.id"), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("from_status", sa.String(50)),
        sa.Column("to_status", sa.String(50)),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_table(
        "issue_attachments",
        *base_columns(),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("issues.id"), nullable=False),
        sa.Column("uploaded_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("thumbnail_url", sa.Text()),
        sa.Column("medium_url", sa.Text()),
        sa.Column("attachment_type", sa.String(32), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("latitude", sa.Numeric(10, 7)),
        sa.Column("longitude", sa.Numeric(10, 7)),
        sa.Column("taken_at", sa.DateTime(timezone=True)),
        sa.Column("perceptual_hash", sa.String(128)),
        sa.Column("antifraud_flags", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_table(
        "exif_data",
        *base_columns(),
        sa.Column("attachment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("issue_attachments.id"), nullable=False, unique=True),
        sa.Column("raw_exif", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_table(
        "issue_comments",
        *base_columns(),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("issues.id"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("language", sa.String(8), nullable=False, server_default="ru"),
        sa.Column("is_internal", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "issue_assignees",
        *base_columns(),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("issues.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_issue_history_issue_id", "issue_history", ["issue_id"])
    op.create_index("ix_issue_attachments_issue_id", "issue_attachments", ["issue_id"])
    op.create_index("ix_issue_comments_issue_id", "issue_comments", ["issue_id"])
    op.create_index("ix_issue_assignees_issue_user", "issue_assignees", ["issue_id", "user_id"])


def downgrade() -> None:
    op.drop_index("ix_issue_assignees_issue_user", table_name="issue_assignees")
    op.drop_index("ix_issue_comments_issue_id", table_name="issue_comments")
    op.drop_index("ix_issue_attachments_issue_id", table_name="issue_attachments")
    op.drop_index("ix_issue_history_issue_id", table_name="issue_history")
    op.drop_table("issue_assignees")
    op.drop_table("issue_comments")
    op.drop_table("exif_data")
    op.drop_table("issue_attachments")
    op.drop_table("issue_history")
    op.execute("DROP INDEX IF EXISTS ix_issues_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_issues_search_gin")
    op.execute("DROP INDEX IF EXISTS ix_issues_geometry_gist")
    op.drop_index("ix_issues_is_overdue", table_name="issues")
    op.drop_index("ix_issues_assigned_to_id", table_name="issues")
    op.drop_index("ix_issues_tenant_status", table_name="issues")
    op.drop_table("issues")
    op.drop_table("issue_number_counters")
    op.drop_index("ix_categories_tenant_code", table_name="categories")
    op.drop_index("ix_districts_tenant_code", table_name="districts")
    op.drop_index("ix_departments_tenant_name", table_name="departments")
    op.drop_table("categories")
    op.drop_table("districts")
    op.drop_table("departments")
