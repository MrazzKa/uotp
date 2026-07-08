import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.issues.models import Issue, IssueHistory
from app.modules.issues.state import OVERDUE_ELIGIBLE_STATUSES
from app.modules.notifications.service import notify_issue_overdue
from app.modules.sla.models import SlaRule


async def resolve_sla_rule(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    category_id: uuid.UUID | None,
    priority: str | None,
) -> SlaRule | None:
    result = await session.execute(
        select(SlaRule).where(
            SlaRule.tenant_id == tenant_id,
            SlaRule.is_active.is_(True),
            SlaRule.deleted_at.is_(None),
            or_(SlaRule.category_id == category_id, SlaRule.category_id.is_(None)),
            or_(SlaRule.priority == priority, SlaRule.priority.is_(None)),
        )
    )
    rules = result.scalars().all()

    def score(rule: SlaRule) -> int:
        value = 0
        if category_id is not None and rule.category_id == category_id:
            value += 2
        if priority is not None and rule.priority == priority:
            value += 1
        return value

    return max(rules, key=score, default=None)


def add_minutes(base_time: datetime, minutes: int, is_24_7: bool = True) -> datetime:
    # Future extension point: business calendar for is_24_7=False.
    return base_time + timedelta(minutes=minutes)


async def apply_sla_deadlines(
    session: AsyncSession,
    issue: Issue,
    *,
    base_time: datetime | None = None,
    include_inspection: bool = False,
) -> None:
    if issue.primary_category_id is None and not issue.priority:
        return
    rule = await resolve_sla_rule(session, issue.tenant_id, issue.primary_category_id, issue.priority)
    if rule is None:
        return
    base = base_time or issue.created_at or datetime.now(UTC)
    issue.reaction_due_at = add_minutes(base, rule.reaction_minutes, rule.is_24_7)
    issue.sla_due_at = add_minutes(base, rule.execution_minutes, rule.is_24_7)
    if include_inspection:
        issue.inspection_due_at = add_minutes(base, rule.inspection_minutes, rule.is_24_7)


async def apply_inspection_deadline(session: AsyncSession, issue: Issue) -> None:
    rule = await resolve_sla_rule(session, issue.tenant_id, issue.primary_category_id, issue.priority)
    if rule is None:
        return
    base = issue.completed_at or datetime.now(UTC)
    issue.inspection_due_at = add_minutes(base, rule.inspection_minutes, rule.is_24_7)


def is_reaction_late(issue: Issue) -> bool:
    if issue.reaction_due_at is None:
        return False
    reacted_at = issue.accepted_at or issue.on_site_at
    return reacted_at is not None and reacted_at > issue.reaction_due_at


def enter_sla_pause(issue: Issue, now: datetime | None = None) -> None:
    if issue.sla_paused_at is None:
        issue.sla_paused_at = now or datetime.now(UTC)


def exit_sla_pause(issue: Issue, now: datetime | None = None) -> None:
    if issue.sla_paused_at is None:
        return
    current = now or datetime.now(UTC)
    pause_delta = current - issue.sla_paused_at
    for field in ("reaction_due_at", "sla_due_at", "inspection_due_at"):
        value = getattr(issue, field)
        if value is not None:
            setattr(issue, field, value + pause_delta)
    issue.sla_paused_at = None


def _overdue_candidate_filters(current: datetime):
    return (
        Issue.deleted_at.is_(None),
        Issue.is_overdue.is_(False),
        Issue.sla_due_at.is_not(None),
        Issue.sla_due_at < current,
        Issue.sla_paused_at.is_(None),
        Issue.status.in_([status.value for status in OVERDUE_ELIGIBLE_STATUSES]),
    )


async def mark_overdue_for_tenant(
    session: AsyncSession, tenant_id: uuid.UUID, now: datetime | None = None
) -> int:
    """Flag overdue issues for a single tenant in its own transaction (idempotent)."""
    current = now or datetime.now(UTC)
    result = await session.execute(
        select(Issue).where(Issue.tenant_id == tenant_id, *_overdue_candidate_filters(current))
    )
    issues = result.scalars().all()
    for issue in issues:
        issue.is_overdue = True
        session.add(
            IssueHistory(
                tenant_id=issue.tenant_id,
                issue_id=issue.id,
                actor_id=None,
                action="sla_overdue",
                from_status=issue.status,
                to_status=issue.status,
                payload={"sla_due_at": issue.sla_due_at.isoformat() if issue.sla_due_at else None},
            )
        )
        await notify_issue_overdue(session, issue)
    await session.commit()
    return len(issues)


async def mark_overdue_issues(session: AsyncSession, now: datetime | None = None) -> int:
    """Sweep overdue issues per tenant, scoping each batch/transaction to one tenant."""
    current = now or datetime.now(UTC)
    tenant_ids = (
        await session.execute(
            select(Issue.tenant_id).where(*_overdue_candidate_filters(current)).distinct()
        )
    ).scalars().all()
    total = 0
    for tenant_id in tenant_ids:
        total += await mark_overdue_for_tenant(session, tenant_id, current)
    return total


async def seed_default_sla_rules(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    # Matches the SLA matrix in the ТЗ §4.3 (reaction / execution / inspection, minutes).
    defaults = [
        ("CRITICAL", 15, 120, 60),
        ("HIGH", 60, 480, 240),
        ("MEDIUM", 240, 1440, 480),
        ("LOW", 1440, 4320, 1440),
        (None, 1440, 4320, 1440),
    ]
    for priority, reaction, execution, inspection in defaults:
        priority_filter = SlaRule.priority == priority if priority else SlaRule.priority.is_(None)
        exists = (
            await session.execute(
                select(SlaRule).where(
                    SlaRule.tenant_id == tenant_id,
                    SlaRule.category_id.is_(None),
                    priority_filter,
                )
            )
        ).scalar_one_or_none()
        if exists is None:
            session.add(
                SlaRule(
                    tenant_id=tenant_id,
                    category_id=None,
                    priority=priority,
                    reaction_minutes=reaction,
                    execution_minutes=execution,
                    inspection_minutes=inspection,
                    is_24_7=True,
                    is_active=True,
                )
            )
