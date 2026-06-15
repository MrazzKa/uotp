"""sla default values + search/trigram indexes cleanup

Revision ID: 0005_sla_values_search_indexes
Revises: 0004_notifications
Create Date: 2026-06-15
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0005_sla_values_search_indexes"
down_revision: Union[str, None] = "0004_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ТЗ §4.3 matrix: priority -> (reaction, execution, inspection) minutes.
SLA_DEFAULTS = {
    "CRITICAL": (15, 120, 60),
    "HIGH": (60, 480, 240),
    "MEDIUM": (240, 1440, 480),
    "LOW": (1440, 4320, 1440),
}
NULL_DEFAULT = (1440, 4320, 1440)


def upgrade() -> None:
    # 1) Reconcile tenant default SLA rules (category-less) with the ТЗ matrix.
    for priority, (reaction, execution, inspection) in SLA_DEFAULTS.items():
        op.execute(
            "UPDATE sla_rules SET reaction_minutes = %d, execution_minutes = %d, "
            "inspection_minutes = %d WHERE category_id IS NULL AND priority = '%s'"
            % (reaction, execution, inspection, priority)
        )
    op.execute(
        "UPDATE sla_rules SET reaction_minutes = %d, execution_minutes = %d, "
        "inspection_minutes = %d WHERE category_id IS NULL AND priority IS NULL"
        % NULL_DEFAULT
    )

    # 2) Trigram index to back ILIKE substring search on issues (DB-01).
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_issues_title_trgm ON issues "
        "USING gin (title gin_trgm_ops, description gin_trgm_ops)"
    )

    # 3) Drop the duplicate geometry index auto-created by geoalchemy2; keep the
    #    explicit ix_issues_geometry_gist (DB-02).
    op.execute("DROP INDEX IF EXISTS idx_issues_geometry")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_issues_title_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_issues_geometry ON issues USING gist (geometry)"
    )
    # SLA value reconciliation is not reverted (no reliable previous-state to restore).
