from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import and_, case, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Department, District, Sphere
from app.modules.issues.models import Issue, IssueAssignee, IssueHistory
from app.modules.issues.state import IssueStatus
from app.modules.users.models import User

LEADERSHIP_ROLES = {"ADMIN", "AKIM", "DEPUTY", "APPARAT"}

OPEN_STATUSES = {
    IssueStatus.NEW,
    IssueStatus.ASSIGNED,
    IssueStatus.REVIEW_CONTROLLER,
    IssueStatus.REVIEW_AUTHOR,
    IssueStatus.ON_HOLD,
}

ON_REVIEW_STATUSES = {IssueStatus.REVIEW_CONTROLLER, IssueStatus.REVIEW_AUTHOR}


def visible_issue_ids_statement(user: User):
    statement = select(Issue.id).where(Issue.tenant_id == user.tenant_id, Issue.deleted_at.is_(None))
    role = user.role.code if user.role else None
    if role not in LEADERSHIP_ROLES and not user.controls_all_spheres:
        conditions = [
            Issue.created_by_id == user.id,
            Issue.controller_id == user.id,
            Issue.assigned_to_id == user.id,
            IssueAssignee.user_id == user.id,
            and_(Issue.sphere_id.is_not(None), Issue.sphere_id == user.sphere_id),
        ]
        if role == "OPERATOR":
            conditions.append(Issue.assigned_to_id.is_(None))
        statement = (
            statement.outerjoin(IssueAssignee, IssueAssignee.issue_id == Issue.id)
            .where(or_(*conditions))
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
                func.count().filter(Issue.status == IssueStatus.ASSIGNED.value).label("in_progress"),
                func.count().filter(Issue.is_overdue.is_(True)).label("overdue"),
                func.count().filter(Issue.status.in_([status.value for status in ON_REVIEW_STATUSES])).label("on_review"),
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

    # Мониторинг по сельским округам: доля закрытых задач у исполнителей округа.
    okrug_rows = (
        await session.execute(
            select(
                Department.id.label("id"),
                Department.name_ru.label("name"),
                func.count(distinct(Issue.id)).label("total"),
                func.count(distinct(Issue.id)).filter(Issue.status == IssueStatus.CLOSED.value).label("done"),
            )
            .select_from(Department)
            .join(User, User.department_id == Department.id)
            .join(Issue, Issue.assigned_to_id == User.id)
            .where(
                Department.tenant_id == user.tenant_id,
                Department.type == "rural_okrug",
                Issue.deleted_at.is_(None),
            )
            .group_by(Department.id, Department.name_ru)
            .order_by(Department.name_ru)
        )
    ).mappings().all()
    okrug_monitoring = [
        {
            "id": row["id"],
            "name": row["name"],
            "total": int(row["total"]),
            "done": int(row["done"]),
            "pct": round(int(row["done"]) / int(row["total"]) * 100) if row["total"] else 0,
        }
        for row in okrug_rows
    ]

    return {
        "counts": {
            "in_progress": int(counts_row.in_progress),
            "overdue": int(counts_row.overdue),
            "on_review": int(counts_row.on_review),
            "closed_today": int(counts_row.closed_today),
            "new": int(counts_row.new),
        },
        "sla_on_time_pct": sla_on_time_pct,
        "per_day": per_day,
        "by_status": by_status,
        "hot_zones": hot_zones,
        "okrug_monitoring": okrug_monitoring,
        "recent_events": recent_events,
    }


def _breakdown(rows) -> list[dict]:
    return [
        {
            "name": row["name"],
            "total": int(row["total"]),
            "done": int(row["done"]),
            "pct": round(int(row["done"]) / int(row["total"]) * 100) if row["total"] else 0,
        }
        for row in rows
    ]


async def okrug_detail(session: AsyncSession, user: User, department_id) -> dict | None:
    """Провал внутрь округа: по специалистам и по сферам."""
    dept = (
        await session.execute(
            select(Department).where(
                Department.id == department_id,
                Department.tenant_id == user.tenant_id,
                Department.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if dept is None:
        return None
    done_filter = Issue.status == IssueStatus.CLOSED.value

    by_user_rows = (
        await session.execute(
            select(
                User.full_name.label("name"),
                func.count(distinct(Issue.id)).label("total"),
                func.count(distinct(Issue.id)).filter(done_filter).label("done"),
            )
            .select_from(User)
            .outerjoin(Issue, (Issue.assigned_to_id == User.id) & (Issue.deleted_at.is_(None)))
            .where(User.department_id == department_id, User.tenant_id == user.tenant_id, User.deleted_at.is_(None))
            .group_by(User.full_name)
            .order_by(User.full_name)
        )
    ).mappings().all()

    by_sphere_rows = (
        await session.execute(
            select(
                Sphere.name_ru.label("name"),
                func.count(distinct(Issue.id)).label("total"),
                func.count(distinct(Issue.id)).filter(done_filter).label("done"),
            )
            .select_from(Issue)
            .join(User, Issue.assigned_to_id == User.id)
            .join(Sphere, Issue.sphere_id == Sphere.id)
            .where(User.department_id == department_id, Issue.deleted_at.is_(None))
            .group_by(Sphere.name_ru)
            .order_by(Sphere.name_ru)
        )
    ).mappings().all()

    return {"name": dept.name_ru, "by_user": _breakdown(by_user_rows), "by_sphere": _breakdown(by_sphere_rows)}
