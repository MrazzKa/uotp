"""sphere controller: контролёр как атрибут сферы

Revision ID: 0008_sphere_controller
Revises: 0007_v3_task_model
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0008_sphere_controller"
down_revision: Union[str, None] = "0007_v3_task_model"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "spheres",
        sa.Column("controller_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("spheres", "controller_id")
