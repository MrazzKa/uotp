import uuid
from datetime import UTC, datetime, timedelta

import pytest

# Import the full model set so SQLAlchemy can configure Issue's relationships.
import app.modules.catalog.models  # noqa: F401
import app.modules.notifications.models  # noqa: F401
import app.modules.roles.models  # noqa: F401
import app.modules.users.models  # noqa: F401
from app.modules.issues.models import Issue
from app.modules.issues.state import IssueStatus
from app.modules.sla.models import SlaRule
from app.modules.sla.service import (
    apply_sla_deadlines,
    enter_sla_pause,
    exit_sla_pause,
    mark_overdue_for_tenant,
    mark_overdue_issues,
    resolve_sla_rule,
)


class _ScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class _Result:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return _ScalarResult(self.rows)


class _Session:
    def __init__(self, rows):
        self.rows = rows
        self.added = []
        self.commits = 0

    async def execute(self, _statement):
        return _Result(self.rows)

    def add(self, row):
        self.added.append(row)

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_resolve_sla_rule_prefers_exact_match() -> None:
    tenant_id = uuid.uuid4()
    category_id = uuid.uuid4()
    default = SlaRule(tenant_id=tenant_id, category_id=None, priority=None, reaction_minutes=240, execution_minutes=1440, inspection_minutes=1440)
    priority = SlaRule(tenant_id=tenant_id, category_id=None, priority="HIGH", reaction_minutes=120, execution_minutes=480, inspection_minutes=1440)
    category = SlaRule(tenant_id=tenant_id, category_id=category_id, priority=None, reaction_minutes=90, execution_minutes=360, inspection_minutes=1440)
    exact = SlaRule(tenant_id=tenant_id, category_id=category_id, priority="HIGH", reaction_minutes=30, execution_minutes=180, inspection_minutes=720)

    rule = await resolve_sla_rule(_Session([default, priority, category, exact]), tenant_id, category_id, "HIGH")

    assert rule is exact


@pytest.mark.asyncio
async def test_apply_sla_deadlines_sets_create_deadlines() -> None:
    tenant_id = uuid.uuid4()
    category_id = uuid.uuid4()
    base = datetime(2026, 6, 11, 8, 0, tzinfo=UTC)
    issue = Issue(tenant_id=tenant_id, primary_category_id=category_id, priority="MEDIUM")
    rule = SlaRule(tenant_id=tenant_id, category_id=category_id, priority="MEDIUM", reaction_minutes=15, execution_minutes=60, inspection_minutes=120)

    await apply_sla_deadlines(_Session([rule]), issue, base_time=base, include_inspection=True)

    assert issue.reaction_due_at == base + timedelta(minutes=15)
    assert issue.sla_due_at == base + timedelta(minutes=60)
    assert issue.inspection_due_at == base + timedelta(minutes=120)


def test_pause_resume_shifts_due_dates() -> None:
    start = datetime(2026, 6, 11, 8, 0, tzinfo=UTC)
    issue = Issue(
        reaction_due_at=start + timedelta(hours=1),
        sla_due_at=start + timedelta(hours=2),
        inspection_due_at=start + timedelta(hours=3),
    )

    enter_sla_pause(issue, start)
    exit_sla_pause(issue, start + timedelta(minutes=30))

    assert issue.sla_paused_at is None
    assert issue.reaction_due_at == start + timedelta(hours=1, minutes=30)
    assert issue.sla_due_at == start + timedelta(hours=2, minutes=30)
    assert issue.inspection_due_at == start + timedelta(hours=3, minutes=30)


@pytest.mark.asyncio
async def test_mark_overdue_for_tenant_sets_flag_and_history() -> None:
    now = datetime(2026, 6, 11, 12, 0, tzinfo=UTC)
    tenant_id = uuid.uuid4()
    issue = Issue(
        tenant_id=tenant_id,
        id=uuid.uuid4(),
        status=IssueStatus.ASSIGNED,
        is_overdue=False,
        sla_due_at=now - timedelta(minutes=1),
    )
    session = _Session([issue])

    count = await mark_overdue_for_tenant(session, tenant_id, now)

    assert count == 1
    assert issue.is_overdue is True
    assert session.commits == 1
    assert session.added[0].action == "sla_overdue"


class _QueueSession:
    """Returns queued result-row-sets in order, one per execute()."""

    def __init__(self, result_sets):
        self._queue = list(result_sets)
        self.added = []
        self.commits = 0

    async def execute(self, _statement):
        return _Result(self._queue.pop(0))

    def add(self, row):
        self.added.append(row)

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_mark_overdue_issues_iterates_per_tenant() -> None:
    now = datetime(2026, 6, 11, 12, 0, tzinfo=UTC)
    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
    issue_a = Issue(tenant_id=tenant_a, id=uuid.uuid4(), status=IssueStatus.ASSIGNED,
                    is_overdue=False, sla_due_at=now - timedelta(minutes=1))
    issue_b = Issue(tenant_id=tenant_b, id=uuid.uuid4(), status=IssueStatus.ASSIGNED,
                    is_overdue=False, sla_due_at=now - timedelta(minutes=1))
    # execute order: distinct tenant ids, then per tenant (issues, then overdue-recipients).
    session = _QueueSession([[tenant_a, tenant_b], [issue_a], [], [issue_b], []])

    count = await mark_overdue_issues(session, now)

    assert count == 2
    assert issue_a.is_overdue is True and issue_b.is_overdue is True
    assert session.commits == 2  # one transaction per tenant
