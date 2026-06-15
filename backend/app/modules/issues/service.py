import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, UploadFile, status
from geoalchemy2.elements import WKTElement
from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.issues.models import (
    ExifData,
    Issue,
    IssueAssignee,
    IssueAttachment,
    IssueComment,
    IssueHistory,
    IssueNumberCounter,
)
from app.modules.issues.schemas import IssueAssign, IssueCreate, IssueQualify, IssueTransition, IssueUpdate
from app.modules.issues.state import IssueStatus, can_transition
from app.modules.audit.service import log_audit
from app.modules.issues.storage import upload_issue_file
from app.modules.notifications.service import (
    notify_issue_assigned,
    notify_issue_comment,
    notify_issue_completed,
    notify_issue_returned,
)
from app.modules.sla.service import (
    apply_inspection_deadline,
    apply_sla_deadlines,
    enter_sla_pause,
    exit_sla_pause,
    is_reaction_late,
)
from app.modules.users.models import User


def tenant_prefix(tenant_code: str) -> str:
    if tenant_code == "petropavlovsk":
        return "PVL"
    return tenant_code[:3].upper()


def point(latitude: Decimal | None, longitude: Decimal | None):
    if latitude is None or longitude is None:
        return None
    return WKTElement(f"POINT({longitude} {latitude})", srid=4326)


async def next_public_number(session: AsyncSession, tenant_id: uuid.UUID, tenant_code: str) -> str:
    year = datetime.now(UTC).year
    await session.execute(
        insert(IssueNumberCounter)
        .values(tenant_id=tenant_id, year=year, next_number=1)
        .on_conflict_do_nothing(index_elements=["tenant_id", "year"])
    )
    result = await session.execute(
        select(IssueNumberCounter)
        .where(IssueNumberCounter.tenant_id == tenant_id, IssueNumberCounter.year == year)
        .with_for_update()
    )
    counter = result.scalar_one()
    number = counter.next_number
    counter.next_number += 1
    return f"{tenant_prefix(tenant_code)}-{year}-{number:05d}"


READ_ONLY_ROLES = {"AKIM"}
ISSUE_CREATE_ROLES = {"ADMIN", "DISPATCHER", "EXECUTOR"}


def ensure_can_write(actor: User) -> None:
    """Block read-only roles (AKIM) from any write action."""
    if actor.role is None or actor.role.code in READ_ONLY_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Read-only role")


def ensure_can_create_issue(actor: User, source: str) -> None:
    role = actor.role.code if actor.role else None
    if role not in ISSUE_CREATE_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to create issues")
    # Field executors may only file issues from the mobile app.
    if role == "EXECUTOR" and source != "app":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Executors can only create issues from the mobile app",
        )


def require_transition(role: str, from_status: str, to_status: str) -> None:
    if not can_transition(role, from_status, to_status):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transition {from_status}->{to_status} is not allowed for role {role}",
        )


async def add_history(
    session: AsyncSession,
    issue: Issue,
    actor: User,
    action: str,
    from_status: str | None = None,
    to_status: str | None = None,
    payload: dict | None = None,
) -> IssueHistory:
    entry = IssueHistory(
        tenant_id=issue.tenant_id,
        issue_id=issue.id,
        actor_id=actor.id,
        action=action,
        from_status=from_status,
        to_status=to_status,
        payload=payload or {},
    )
    session.add(entry)
    return entry


def apply_role_visibility(statement, user: User):
    role = user.role.code
    statement = statement.where(Issue.tenant_id == user.tenant_id, Issue.deleted_at.is_(None))
    if role == "EXECUTOR":
        statement = statement.outerjoin(IssueAssignee, IssueAssignee.issue_id == Issue.id).where(
            or_(Issue.assigned_to_id == user.id, IssueAssignee.user_id == user.id)
        )
    return statement


async def get_issue_or_404(session: AsyncSession, issue_id: uuid.UUID, user: User) -> Issue:
    statement = apply_role_visibility(select(Issue).where(Issue.id == issue_id), user)
    result = await session.execute(statement)
    issue = result.unique().scalar_one_or_none()
    if issue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    return issue


async def reload_issue(session: AsyncSession, issue_id: uuid.UUID) -> Issue:
    result = await session.execute(select(Issue).where(Issue.id == issue_id))
    return result.unique().scalar_one()


async def create_issue(session: AsyncSession, payload: IssueCreate, actor: User) -> Issue:
    ensure_can_create_issue(actor, payload.source)
    public_number = await next_public_number(session, actor.tenant_id, actor.tenant.code)
    now = datetime.now(UTC)
    issue = Issue(
        tenant_id=actor.tenant_id,
        public_number=public_number,
        source=payload.source,
        title=payload.title,
        description=payload.description,
        primary_category_id=payload.primary_category_id,
        tags=payload.tags,
        status=IssueStatus.NEW,
        priority=payload.priority,
        address=payload.address,
        latitude=payload.latitude,
        longitude=payload.longitude,
        geometry=point(payload.latitude, payload.longitude),
        district_id=payload.district_id,
        created_by_id=actor.id,
        assigned_to_id=payload.assigned_to_id,
        department_id=payload.department_id,
        created_at=now,
        updated_at=now,
    )
    session.add(issue)
    await session.flush()
    await apply_sla_deadlines(session, issue, base_time=now, include_inspection=True)
    await add_history(session, issue, actor, "created", None, issue.status, {"source": issue.source})
    await log_audit(
        session, actor, "issue.create", "issue",
        entity_id=issue.id, context={"public_number": issue.public_number, "source": issue.source},
    )
    issue_id = issue.id
    await session.commit()
    return await reload_issue(session, issue_id)


async def update_issue(session: AsyncSession, issue: Issue, payload: IssueUpdate, actor: User) -> Issue:
    if actor.role.code not in {"ADMIN", "DISPATCHER"} and actor.id != issue.created_by_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(issue, key, value)
    if "latitude" in data or "longitude" in data:
        issue.geometry = point(issue.latitude, issue.longitude)
    await add_history(session, issue, actor, "updated", issue.status, issue.status, data)
    issue_id = issue.id
    await session.commit()
    return await reload_issue(session, issue_id)


async def soft_delete_issue(session: AsyncSession, issue: Issue, actor: User) -> None:
    if actor.role.code not in {"ADMIN", "DISPATCHER"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    issue.deleted_at = datetime.now(UTC)
    await add_history(session, issue, actor, "deleted", issue.status, issue.status)
    await session.commit()


async def qualify_issue(session: AsyncSession, issue: Issue, payload: IssueQualify, actor: User) -> Issue:
    if issue.status == IssueStatus.NEW:
        require_transition(actor.role.code, issue.status, IssueStatus.QUALIFICATION)
        from_status = issue.status
        issue.status = IssueStatus.QUALIFICATION
    elif issue.status == IssueStatus.QUALIFICATION and actor.role.code in {"ADMIN", "DISPATCHER"}:
        from_status = issue.status
    else:
        require_transition(actor.role.code, issue.status, IssueStatus.QUALIFICATION)
        from_status = issue.status
    issue.primary_category_id = payload.category_id
    issue.priority = payload.priority
    issue.department_id = payload.department_id
    issue.qualified_at = datetime.now(UTC)
    issue.qualified_by_id = actor.id
    await apply_sla_deadlines(session, issue, base_time=issue.created_at, include_inspection=True)
    await add_history(
        session,
        issue,
        actor,
        "qualified",
        from_status,
        issue.status,
        payload.model_dump(mode="json"),
    )
    issue_id = issue.id
    await session.commit()
    return await reload_issue(session, issue_id)


async def assign_issue(session: AsyncSession, issue: Issue, payload: IssueAssign, actor: User) -> Issue:
    require_transition(actor.role.code, issue.status, IssueStatus.ASSIGNED)
    from_status = issue.status
    issue.status = IssueStatus.ASSIGNED
    exit_sla_pause(issue)
    issue.assigned_to_id = payload.assigned_to_id
    if payload.department_id:
        issue.department_id = payload.department_id
    session.add(
        IssueAssignee(
            tenant_id=issue.tenant_id,
            issue_id=issue.id,
            user_id=payload.assigned_to_id,
            is_primary=True,
        )
    )
    await add_history(
        session,
        issue,
        actor,
        "assigned",
        from_status,
        issue.status,
        payload.model_dump(mode="json"),
    )
    await notify_issue_assigned(session, issue)
    issue_id = issue.id
    await session.commit()
    return await reload_issue(session, issue_id)


async def transition_issue(
    session: AsyncSession, issue: Issue, payload: IssueTransition, actor: User
) -> Issue:
    require_transition(actor.role.code, issue.status, payload.status)
    from_status = issue.status
    to_status = payload.status
    if to_status == IssueStatus.RETURNED:
        issue.reopen_count += 1
        issue.status = IssueStatus.ASSIGNED
        history_to = IssueStatus.RETURNED
        enter_sla_pause(issue)
    else:
        issue.status = to_status
        history_to = to_status
        exit_sla_pause(issue)
    now = datetime.now(UTC)
    if issue.status == IssueStatus.ACCEPTED:
        issue.accepted_at = now
        await add_history(
            session,
            issue,
            actor,
            "sla_reaction_violated" if is_reaction_late(issue) else "sla_reaction_met",
            from_status,
            history_to,
            {"reaction_due_at": issue.reaction_due_at.isoformat() if issue.reaction_due_at else None},
        )
    if issue.status == IssueStatus.IN_PROGRESS:
        issue.on_site_at = now
        await add_history(
            session,
            issue,
            actor,
            "sla_reaction_violated" if is_reaction_late(issue) else "sla_reaction_met",
            from_status,
            history_to,
            {"reaction_due_at": issue.reaction_due_at.isoformat() if issue.reaction_due_at else None},
        )
    if issue.status == IssueStatus.COMPLETED:
        issue.completed_at = now
        await apply_inspection_deadline(session, issue)
    if issue.status == IssueStatus.CLOSED:
        issue.closed_at = now
    await add_history(session, issue, actor, "transitioned", from_status, history_to, payload.payload)
    await log_audit(
        session, actor, "issue.transition", "issue",
        entity_id=issue.id, context={"from": str(from_status), "to": str(history_to)},
    )
    if to_status == IssueStatus.RETURNED:
        await notify_issue_returned(session, issue)
    elif issue.status == IssueStatus.COMPLETED:
        await notify_issue_completed(session, issue)
    issue_id = issue.id
    await session.commit()
    return await reload_issue(session, issue_id)


async def mark_on_site(session: AsyncSession, issue: Issue, actor: User) -> Issue:
    return await transition_issue(
        session, issue, IssueTransition(status=IssueStatus.IN_PROGRESS, payload={"source": "on-site"}), actor
    )


async def add_comment(session: AsyncSession, issue: Issue, actor: User, content: str, language: str, is_internal: bool):
    ensure_can_write(actor)
    comment = IssueComment(
        tenant_id=issue.tenant_id,
        issue_id=issue.id,
        author_id=actor.id,
        content=content,
        language=language,
        is_internal=is_internal,
    )
    session.add(comment)
    await add_history(session, issue, actor, "commented", issue.status, issue.status, {"is_internal": is_internal})
    await notify_issue_comment(session, issue, actor)
    await session.commit()
    return comment


async def add_attachments(
    session: AsyncSession,
    issue: Issue,
    actor: User,
    files: list[UploadFile],
    attachment_type: str,
    latitude: Decimal | None = None,
    longitude: Decimal | None = None,
    taken_at: datetime | None = None,
) -> list[IssueAttachment]:
    ensure_can_write(actor)
    created = []
    for file in files:
        data = await upload_issue_file(issue.tenant_id, issue.id, file)
        attachment = IssueAttachment(
            tenant_id=issue.tenant_id,
            issue_id=issue.id,
            uploaded_by_id=actor.id,
            file_url=data["file_url"],
            thumbnail_url=data["thumbnail_url"],
            medium_url=data["medium_url"],
            attachment_type=attachment_type,
            mime_type=data["mime_type"],
            size_bytes=data["size_bytes"],
            latitude=latitude,
            longitude=longitude,
            taken_at=taken_at,
            perceptual_hash=data["perceptual_hash"],
            antifraud_flags={},
        )
        session.add(attachment)
        await session.flush()
        if data["raw_exif"]:
            session.add(
                ExifData(
                    tenant_id=issue.tenant_id,
                    attachment_id=attachment.id,
                    raw_exif=data["raw_exif"],
                )
            )
        created.append(attachment)
    await add_history(session, issue, actor, "attached", issue.status, issue.status, {"count": len(created)})
    # Attachments carry personal data (photos, EXIF, geo) — record the access.
    await log_audit(
        session, actor, "attachment.upload", "issue",
        entity_id=issue.id,
        context={"count": len(created), "attachment_type": attachment_type},
    )
    await session.commit()
    return created


async def list_issues(
    session: AsyncSession,
    user: User,
    *,
    status_value: str | None = None,
    category_id: uuid.UUID | None = None,
    district_id: uuid.UUID | None = None,
    assigned_to_id: uuid.UUID | None = None,
    priority: str | None = None,
    source: str | None = None,
    is_overdue: bool | None = None,
    q: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
) -> tuple[list[Issue], str | None]:
    statement = apply_role_visibility(select(Issue), user)
    filters = []
    if status_value:
        filters.append(Issue.status == status_value)
    if category_id:
        filters.append(Issue.primary_category_id == category_id)
    if district_id:
        filters.append(Issue.district_id == district_id)
    if assigned_to_id:
        filters.append(Issue.assigned_to_id == assigned_to_id)
    if priority:
        filters.append(Issue.priority == priority)
    if source:
        filters.append(Issue.source == source)
    if is_overdue is not None:
        filters.append(Issue.is_overdue.is_(is_overdue))
    if q:
        pattern = f"%{q}%"
        filters.append(
            or_(
                Issue.title.ilike(pattern),
                Issue.description.ilike(pattern),
                Issue.public_number.ilike(pattern),
            )
        )
    if cursor:
        created_raw, _, id_raw = cursor.partition("|")
        created_dt = datetime.fromisoformat(created_raw)
        if id_raw:
            filters.append(
                or_(
                    Issue.created_at < created_dt,
                    and_(Issue.created_at == created_dt, Issue.id < uuid.UUID(id_raw)),
                )
            )
        else:
            filters.append(Issue.created_at < created_dt)
    if filters:
        statement = statement.where(and_(*filters))
    statement = statement.order_by(Issue.created_at.desc(), Issue.id.desc()).limit(limit + 1)
    result = await session.execute(statement)
    items = result.unique().scalars().all()
    next_cursor = None
    if len(items) > limit:
        last = items[limit - 1]
        next_cursor = f"{last.created_at.isoformat()}|{last.id}"
        items = items[:limit]
    return items, next_cursor
