import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException, UploadFile, status
from geoalchemy2.elements import WKTElement
from sqlalchemy import and_, delete, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import log_audit
from app.modules.catalog.models import Sphere
from app.modules.issues.models import (
    ExifData,
    Issue,
    IssueAssignee,
    IssueAttachment,
    IssueComment,
    IssueHistory,
    IssueNumberCounter,
    IssuePersonalMark,
)
from app.modules.issues.schemas import (
    IssueAssign,
    IssueCreate,
    IssuePersonalControl,
    IssueTransition,
    IssueUpdate,
)
from app.modules.issues.state import (
    OVERDUE_ELIGIBLE_STATUSES,
    IssueStatus,
    TaskRole,
    can_transition,
)
from app.modules.issues.storage import upload_issue_file
from app.modules.notifications.service import (
    notify_issue_assigned,
    notify_issue_closed,
    notify_issue_comment,
    notify_issue_returned,
    notify_issue_submitted,
    notify_issue_to_author,
)
from app.modules.users.models import User

# Роли-руководители: видят весь тенант (аким района, замы, рук. аппарата, админ).
LEADERSHIP_ROLES = {"ADMIN", "AKIM", "DEPUTY", "APPARAT"}
# Роли, которые могут распределять нераспределённые задачи (кроме автора).
DISTRIBUTOR_ROLES = {"ADMIN", "OPERATOR"}

# Срок по умолчанию в зависимости от важности (минуты рабочего времени, упрощённо).
IMPORTANCE_DUE_MINUTES = {"URGENT": 240, "IMPORTANT": 1440, "NORMAL": 4320}


def tenant_prefix(tenant_code: str) -> str:
    if tenant_code == "petropavlovsk":
        return "PVL"
    return tenant_code[:3].upper()


def point(latitude: Decimal | None, longitude: Decimal | None):
    if latitude is None or longitude is None:
        return None
    return WKTElement(f"POINT({longitude} {latitude})", srid=4326)


def default_due_at(importance: str, base: datetime) -> datetime:
    return base + timedelta(minutes=IMPORTANCE_DUE_MINUTES.get(importance, 4320))


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


def task_roles_for(issue: Issue, user: User) -> set[str]:
    """Роли пользователя в конкретной задаче (для проверки переходов)."""
    roles: set[str] = set()
    if user.role is not None and user.role.code == "ADMIN":
        roles.add(TaskRole.ADMIN)
    if issue.created_by_id == user.id:
        roles.add(TaskRole.AUTHOR)
    if issue.controller_id == user.id:
        roles.add(TaskRole.CONTROLLER)
    for assignee in issue.assignees:
        if assignee.user_id == user.id:
            roles.add(TaskRole.CO_EXECUTOR if assignee.role == "CO_EXECUTOR" else TaskRole.EXECUTOR)
    return roles


def can_user_transition(issue: Issue, user: User, to_status: str) -> bool:
    # Личный контроль: снять с контроля задачу, взятую на личный контроль, может только тот,
    # кто её отметил (обычно аким). Остальные задачи снимают контролёр и автор как обычно.
    if to_status in (IssueStatus.CLOSED, IssueStatus.CLOSED.value):
        marks = getattr(issue, "personal_marks", None) or []
        if marks:
            owner_ids = {mark.user_id for mark in marks}
            is_admin = bool(user.role and user.role.code == "ADMIN")
            if user.id not in owner_ids and not is_admin:
                return False
    return any(can_transition(role, issue.status, to_status) for role in task_roles_for(issue, user))


def require_user_transition(issue: Issue, user: User, to_status: str) -> None:
    if not can_user_transition(issue, user, to_status):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transition {issue.status}->{to_status} is not allowed for this user",
        )


async def find_controller_for_sphere(
    session: AsyncSession, tenant_id: uuid.UUID, sphere_id: uuid.UUID | None
) -> uuid.UUID | None:
    """Контролёр по сфере: сначала закреплённый за самой сферой, затем «контролирует все»."""
    if sphere_id is None:
        return None
    sphere = await session.get(Sphere, sphere_id)
    if sphere is not None and sphere.controller_id is not None:
        return sphere.controller_id
    result = await session.execute(
        select(User)
        .where(
            User.tenant_id == tenant_id,
            User.is_active.is_(True),
            or_(User.sphere_id == sphere_id, User.controls_all_spheres.is_(True)),
        )
        .order_by(User.controls_all_spheres.asc())
        .limit(1)
    )
    user = result.scalar_one_or_none()
    return user.id if user is not None else None


def recompute_overdue(issue: Issue, now: datetime | None = None) -> None:
    current = now or datetime.now(UTC)
    issue.is_overdue = bool(
        issue.due_at
        and issue.due_at < current
        and issue.status in OVERDUE_ELIGIBLE_STATUSES
        and issue.sla_paused_at is None
    )


async def add_history(
    session: AsyncSession,
    issue: Issue,
    actor: User | None,
    action: str,
    from_status: str | None = None,
    to_status: str | None = None,
    payload: dict | None = None,
) -> IssueHistory:
    entry = IssueHistory(
        tenant_id=issue.tenant_id,
        issue_id=issue.id,
        actor_id=actor.id if actor is not None else None,
        action=action,
        from_status=from_status,
        to_status=to_status,
        payload=payload or {},
    )
    session.add(entry)
    return entry


def apply_role_visibility(statement, user: User):
    """v3-видимость: руководство видит весь тенант; остальные — свои задачи по ролям и сфере."""
    statement = statement.where(Issue.tenant_id == user.tenant_id, Issue.deleted_at.is_(None))
    role = user.role.code if user.role else None
    if role in LEADERSHIP_ROLES or user.controls_all_spheres:
        return statement
    conditions = [
        Issue.created_by_id == user.id,
        Issue.controller_id == user.id,
        Issue.assigned_to_id == user.id,
        IssueAssignee.user_id == user.id,
        and_(Issue.sphere_id.is_not(None), Issue.sphere_id == user.sphere_id),
    ]
    if role == "OPERATOR":
        # Оператор видит нераспределённые задачи, чтобы их распределять.
        conditions.append(Issue.assigned_to_id.is_(None))
    statement = statement.outerjoin(IssueAssignee, IssueAssignee.issue_id == Issue.id).where(or_(*conditions))
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


async def _sync_assignees(session: AsyncSession, issue: Issue, executor_ids, co_executor_ids) -> None:
    """Пересобрать список исполнителей/соисполнителей задачи (без чтения ленивой связи)."""
    await session.execute(delete(IssueAssignee).where(IssueAssignee.issue_id == issue.id))
    for index, user_id in enumerate(executor_ids):
        session.add(
            IssueAssignee(
                tenant_id=issue.tenant_id,
                issue_id=issue.id,
                user_id=user_id,
                is_primary=index == 0,
                role="EXECUTOR",
            )
        )
    for user_id in co_executor_ids:
        session.add(
            IssueAssignee(
                tenant_id=issue.tenant_id,
                issue_id=issue.id,
                user_id=user_id,
                is_primary=False,
                role="CO_EXECUTOR",
            )
        )
    issue.assigned_to_id = executor_ids[0] if executor_ids else None


async def create_issue(session: AsyncSession, payload: IssueCreate, actor: User) -> Issue:
    public_number = await next_public_number(session, actor.tenant_id, actor.tenant.code)
    now = datetime.now(UTC)
    executor_ids = [uid for uid in payload.executor_ids]
    controller_id = payload.controller_id or await find_controller_for_sphere(
        session, actor.tenant_id, payload.sphere_id
    )
    if payload.source == "voice":
        initial_status = IssueStatus.DRAFT
    elif executor_ids:
        initial_status = IssueStatus.ASSIGNED
    else:
        initial_status = IssueStatus.NEW
    due_at = payload.due_at or default_due_at(payload.importance, now)

    issue = Issue(
        tenant_id=actor.tenant_id,
        public_number=public_number,
        source=payload.source,
        task_type=payload.task_type,
        title=payload.title,
        description=payload.description or payload.title,
        primary_category_id=payload.primary_category_id,
        tags=payload.tags,
        status=initial_status,
        priority=payload.priority,
        importance=payload.importance,
        sphere_id=payload.sphere_id,
        controller_id=controller_id,
        due_at=due_at,
        sla_due_at=due_at,
        address=payload.address,
        latitude=payload.latitude,
        longitude=payload.longitude,
        geometry=point(payload.latitude, payload.longitude),
        district_id=payload.district_id,
        created_by_id=actor.id,
        created_at=now,
        updated_at=now,
    )
    session.add(issue)
    await session.flush()
    await _sync_assignees(session, issue, executor_ids, payload.co_executor_ids)
    recompute_overdue(issue, now)
    await add_history(session, issue, actor, "created", None, issue.status, {"source": issue.source})
    await log_audit(
        session, actor, "issue.create", "issue",
        entity_id=issue.id, context={"public_number": issue.public_number, "source": issue.source},
    )
    issue_id = issue.id
    notify_assigned = issue.status == IssueStatus.ASSIGNED
    await session.commit()
    issue = await reload_issue(session, issue_id)
    if notify_assigned:
        await notify_issue_assigned(session, issue)
        await session.commit()
    return issue


async def update_issue(session: AsyncSession, issue: Issue, payload: IssueUpdate, actor: User) -> Issue:
    is_author = actor.id == issue.created_by_id
    is_admin = actor.role is not None and actor.role.code == "ADMIN"
    if not (is_author or is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    # До ответа исполнителя автор меняет что угодно; после — редактирование ограничено.
    if issue.status not in {IssueStatus.DRAFT, IssueStatus.NEW, IssueStatus.ASSIGNED} and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Editing is limited once the task is under review",
        )
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(issue, key, value)
    if "latitude" in data or "longitude" in data:
        issue.geometry = point(issue.latitude, issue.longitude)
    if "importance" in data and "due_at" not in data and issue.due_at is None:
        issue.due_at = default_due_at(issue.importance, datetime.now(UTC))
        issue.sla_due_at = issue.due_at
    recompute_overdue(issue)
    await add_history(session, issue, actor, "updated", issue.status, issue.status, data)
    issue_id = issue.id
    await session.commit()
    return await reload_issue(session, issue_id)


async def soft_delete_issue(session: AsyncSession, issue: Issue, actor: User) -> None:
    is_author = actor.id == issue.created_by_id
    is_admin = actor.role is not None and actor.role.code == "ADMIN"
    if not (is_author or is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    issue.deleted_at = datetime.now(UTC)
    await add_history(session, issue, actor, "deleted", issue.status, issue.status)
    await session.commit()


async def assign_issue(session: AsyncSession, issue: Issue, payload: IssueAssign, actor: User) -> Issue:
    """Распределение: назначить исполнителей (и опц. контролёра/срок). NEW/DRAFT -> ASSIGNED."""
    is_author = actor.id == issue.created_by_id
    is_distributor = actor.role is not None and actor.role.code in DISTRIBUTOR_ROLES
    if not (is_author or is_distributor):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to distribute")
    if not payload.executor_ids:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No executors")
    from_status = issue.status
    await _sync_assignees(session, issue, payload.executor_ids, payload.co_executor_ids)
    if payload.controller_id is not None:
        issue.controller_id = payload.controller_id
    if payload.due_at is not None:
        issue.due_at = payload.due_at
        issue.sla_due_at = payload.due_at
    issue.status = IssueStatus.ASSIGNED
    issue.sla_paused_at = None
    recompute_overdue(issue)
    await add_history(session, issue, actor, "assigned", from_status, issue.status, payload.model_dump(mode="json"))
    issue_id = issue.id
    await session.commit()
    issue = await reload_issue(session, issue_id)
    await notify_issue_assigned(session, issue)
    await session.commit()
    return issue


async def submit_issue(session: AsyncSession, issue: Issue, actor: User, report: str | None = None) -> Issue:
    """Исполнитель отмечает «Сделал»: к контролёру, а если его нет — сразу автору."""
    target = IssueStatus.REVIEW_CONTROLLER if issue.controller_id else IssueStatus.REVIEW_AUTHOR
    require_user_transition(issue, actor, target)
    from_status = issue.status
    issue.status = target
    recompute_overdue(issue)
    await add_history(session, issue, actor, "submitted", from_status, target, {"report": report} if report else {})
    if report:
        session.add(
            IssueComment(
                tenant_id=issue.tenant_id,
                issue_id=issue.id,
                author_id=actor.id,
                content=report,
                language="ru",
                is_internal=False,
            )
        )
    issue_id = issue.id
    await session.commit()
    issue = await reload_issue(session, issue_id)
    await notify_issue_submitted(session, issue)
    await session.commit()
    return issue


async def transition_issue(
    session: AsyncSession, issue: Issue, payload: IssueTransition, actor: User
) -> Issue:
    """Переходы контролёра/автора: снять с контроля, вернуть на доработку, передать автору, пауза."""
    to_status = payload.status
    require_user_transition(issue, actor, to_status)
    from_status = issue.status
    now = datetime.now(UTC)
    action = "transitioned"
    if to_status == IssueStatus.ASSIGNED and from_status in {
        IssueStatus.REVIEW_CONTROLLER,
        IssueStatus.REVIEW_AUTHOR,
    }:
        issue.reopen_count += 1
        action = "returned"
    if to_status == IssueStatus.ON_HOLD:
        issue.sla_paused_at = now
    if from_status == IssueStatus.ON_HOLD:
        issue.sla_paused_at = None
    issue.status = to_status
    if to_status == IssueStatus.CLOSED:
        issue.closed_at = now
    recompute_overdue(issue, now)
    await add_history(session, issue, actor, action, from_status, to_status, payload.payload)
    await log_audit(
        session, actor, "issue.transition", "issue",
        entity_id=issue.id, context={"from": str(from_status), "to": str(to_status)},
    )
    issue_id = issue.id
    returned = action == "returned"
    to_author = to_status == IssueStatus.REVIEW_AUTHOR and from_status == IssueStatus.REVIEW_CONTROLLER
    closed = to_status == IssueStatus.CLOSED
    await session.commit()
    issue = await reload_issue(session, issue_id)
    if returned:
        await notify_issue_returned(session, issue)
        await session.commit()
    elif to_author:
        await notify_issue_to_author(session, issue)
        await session.commit()
    elif closed:
        await notify_issue_closed(session, issue)
        await session.commit()
    return issue


async def set_personal_control(
    session: AsyncSession, issue: Issue, actor: User, payload: IssuePersonalControl
) -> Issue:
    """Личный контроль: пользователь берёт задачу на свой контроль (галочка + важность)."""
    result = await session.execute(
        select(IssuePersonalMark).where(
            IssuePersonalMark.issue_id == issue.id, IssuePersonalMark.user_id == actor.id
        )
    )
    mark = result.scalar_one_or_none()
    if payload.on:
        if mark is None:
            session.add(
                IssuePersonalMark(
                    tenant_id=issue.tenant_id,
                    issue_id=issue.id,
                    user_id=actor.id,
                    importance=payload.importance,
                )
            )
        else:
            mark.importance = payload.importance
    elif mark is not None:
        await session.delete(mark)
    await add_history(
        session, issue, actor, "personal_control",
        issue.status, issue.status, {"on": payload.on, "importance": payload.importance},
    )
    issue_id = issue.id
    await session.commit()
    return await reload_issue(session, issue_id)


async def add_comment(
    session: AsyncSession, issue: Issue, actor: User, content: str, language: str, is_internal: bool
):
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
                ExifData(tenant_id=issue.tenant_id, attachment_id=attachment.id, raw_exif=data["raw_exif"])
            )
        created.append(attachment)
    await add_history(session, issue, actor, "attached", issue.status, issue.status, {"count": len(created)})
    await log_audit(
        session, actor, "attachment.upload", "issue",
        entity_id=issue.id, context={"count": len(created), "attachment_type": attachment_type},
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
    sphere_id: uuid.UUID | None = None,
    importance: str | None = None,
    priority: str | None = None,
    source: str | None = None,
    is_overdue: bool | None = None,
    personal: bool | None = None,
    mine: bool | None = None,
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
    if sphere_id:
        filters.append(Issue.sphere_id == sphere_id)
    if importance:
        filters.append(Issue.importance == importance)
    if priority:
        filters.append(Issue.priority == priority)
    if source:
        filters.append(Issue.source == source)
    if is_overdue is not None:
        filters.append(Issue.is_overdue.is_(is_overdue))
    if mine:
        # Прямая причастность: я исполнитель, контролёр или автор.
        filters.append(
            or_(
                Issue.assigned_to_id == user.id,
                Issue.controller_id == user.id,
                Issue.created_by_id == user.id,
            )
        )
    if personal:
        statement = statement.join(
            IssuePersonalMark,
            and_(IssuePersonalMark.issue_id == Issue.id, IssuePersonalMark.user_id == user.id),
        )
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
