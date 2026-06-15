from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import case, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import District
from app.modules.issues.models import Issue, IssueAssignee, IssueHistory
from app.modules.issues.state import IssueStatus
from app.modules.users.models import User

OPEN_STATUSES = {
    IssueStatus.NEW,
    IssueStatus.QUALIFICATION,
    IssueStatus.ASSIGNED,
    IssueStatus.ACCEPTED,
    IssueStatus.IN_PROGRESS,
    IssueStatus.COMPLETED,
    IssueStatus.INSPECTION,
    IssueStatus.RETURNED,
}

IN_PROGRESS_STATUSES = {
    IssueStatus.QUALIFICATION,
    IssueStatus.ASSIGNED,
    IssueStatus.ACCEPTED,
    IssueStatus.IN_PROGRESS,
}


def visible_issue_ids_statement(user: User):
    statement = select(Issue.id).where(Issue.tenant_id == user.tenant_id, Issue.deleted_at.is_(None))
    if user.role.code == "EXECUTOR":
        statement = (
            statement.outerjoin(IssueAssignee, IssueAssignee.issue_id == Issue.id)
            .where(or_(Issue.assigned_to_id == user.id, IssueAssignee.user_id == user.id))
            .distinct()
        )
    return statement


def _tenant_timezone(user: User) -> tuple[str, ZoneInfo]:
    tz_name = (user.tenant.timezone if user.tenant and user.tenant.timezone else "UTC") or "UTC"
    try:
        return tz_name, ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        return "UTC", ZoneInfo("UTC")


async def dashboard_summary(session: AsyncSession, user: User) -> dict:
    tz_name, tz = _tenant_timezone(user)
    now = datetime.now(tz)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    period_start = today_start - timedelta(days=13)
    # Day boundary in the tenant's local timezone for per-day grouping.
    local_date = func.date(func.timezone(tz_name, Issue.created_at))
    visible = visible_issue_ids_statement(user).subquery()

    counts_row = (
        await session.execute(
            select(
                func.count().filter(Issue.status.in_([status.value for status in IN_PROGRESS_STATUSES])).label("in_progress"),
                func.count().filter(Issue.is_overdue.is_(True)).label("overdue"),
                func.count().filter(Issue.status == IssueStatus.INSPECTION.value).label("inspection"),
                func.count()
                .filter(Issue.status == IssueStatus.CLOSED.value, Issue.closed_at >= today_start)
                .label("closed_today"),
                func.count().filter(Issue.status == IssueStatus.NEW.value).label("new"),
            )
            .select_from(Issue)
            .join(visible, visible.c.id == Issue.id)
        )
    ).one()

    closed_total, closed_on_time = (
        await session.execute(
            select(
                func.count().label("total"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                (Issue.sla_due_at.is_not(None)) & (Issue.closed_at <= Issue.sla_due_at),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("on_time"),
            )
            .select_from(Issue)
            .join(visible, visible.c.id == Issue.id)
            .where(Issue.status == IssueStatus.CLOSED.value, Issue.closed_at >= today_start - timedelta(days=30))
        )
    ).one()
    sla_on_time_pct = round((closed_on_time / closed_total) * 100, 1) if closed_total else 100.0

    per_day_rows = (
        await session.execute(
            select(local_date.label("date"), func.count(distinct(Issue.id)).label("count"))
            .select_from(Issue)
            .join(visible, visible.c.id == Issue.id)
            .where(Issue.created_at >= period_start)
            .group_by(local_date)
            .order_by(local_date)
        )
    ).mappings().all()
    per_day_map = {row["date"]: int(row["count"]) for row in per_day_rows}
    per_day = [
        {"date": (period_start + timedelta(days=offset)).date(), "count": per_day_map.get((period_start + timedelta(days=offset)).date(), 0)}
        for offset in range(14)
    ]

    by_status = [
        {"status": row["status"], "count": int(row["count"])}
        for row in (
            await session.execute(
                select(Issue.status.label("status"), func.count(distinct(Issue.id)).label("count"))
                .select_from(Issue)
                .join(visible, visible.c.id == Issue.id)
                .group_by(Issue.status)
                .order_by(func.count(distinct(Issue.id)).desc())
            )
        ).mappings().all()
    ]

    hot_zones = [
        {
            "district_id": row["district_id"],
            "name": row["name"] or "No district",
            "count": int(row["count"]),
        }
        for row in (
            await session.execute(
                select(
                    Issue.district_id.label("district_id"),
                    District.name_ru.label("name"),
                    func.count(distinct(Issue.id)).label("count"),
                )
                .select_from(Issue)
                .join(visible, visible.c.id == Issue.id)
                .outerjoin(District, District.id == Issue.district_id)
                .where(Issue.status.in_([status.value for status in OPEN_STATUSES]))
                .group_by(Issue.district_id, District.name_ru)
                .order_by(func.count(distinct(Issue.id)).desc())
                .limit(5)
            )
        ).mappings().all()
    ]

    recent_events = [
        {
            "issue_id": row["issue_id"],
            "public_number": row["public_number"],
            "action": row["action"],
            "to_status": row["to_status"],
            "created_at": row["created_at"],
        }
        for row in (
            await session.execute(
                select(
                    IssueHistory.issue_id,
                    Issue.public_number,
                    IssueHistory.action,
                    IssueHistory.to_status,
                    IssueHistory.created_at,
                )
                .join(Issue, Issue.id == IssueHistory.issue_id)
                .join(visible, visible.c.id == Issue.id)
                .order_by(IssueHistory.created_at.desc())
                .limit(8)
            )
        ).mappings().all()
    ]

    return {
        "counts": {
            "in_progress": int(counts_row.in_progress),
            "overdue": int(counts_row.overdue),
            "inspection": int(counts_row.inspection),
            "closed_today": int(counts_row.closed_today),
            "new": int(counts_row.new),
        },
        "sla_on_time_pct": sla_on_time_pct,
        "per_day": per_day,
        "by_status": by_status,
        "hot_zones": hot_zones,
        "recent_events": recent_events,
    }
