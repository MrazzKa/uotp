import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.issues.models import Issue
from app.modules.notifications.models import DeviceToken, Notification
from app.modules.notifications.push import send_expo_push
from app.modules.roles.models import Role
from app.modules.users.models import User

NotificationType = str

MESSAGES: dict[str, dict[str, tuple[str, str]]] = {
    "issue_assigned": {
        "ru": ("Назначена задача {number}", "Вам назначена задача: {title}"),
        "kk": ("Тапсырма тағайындалды {number}", "Сізге тапсырма тағайындалды: {title}"),
    },
    "issue_returned": {
        "ru": ("Задача возвращена {number}", "Задача возвращена на доработку: {title}"),
        "kk": ("Тапсырма қайтарылды {number}", "Тапсырма түзетуге қайтарылды: {title}"),
    },
    "issue_completed": {
        "ru": ("Задача завершена {number}", "Задача отправлена на проверку: {title}"),
        "kk": ("Тапсырма аяқталды {number}", "Тапсырма тексеруге жіберілді: {title}"),
    },
    "issue_overdue": {
        "ru": ("SLA просрочен {number}", "Просрочен срок исполнения задачи: {title}"),
        "kk": ("SLA мерзімі өтті {number}", "Тапсырманы орындау мерзімі өтті: {title}"),
    },
    "issue_comment": {
        "ru": ("Новый комментарий {number}", "В задаче появился новый комментарий: {title}"),
        "kk": ("Жаңа пікір {number}", "Тапсырмада жаңа пікір пайда болды: {title}"),
    },
}


def render_message(notification_type: NotificationType, issue: Issue, language: str) -> tuple[str, str]:
    title_template, body_template = MESSAGES[notification_type].get(
        language, MESSAGES[notification_type]["ru"]
    )
    values = {"number": issue.public_number, "title": issue.title}
    return title_template.format(**values), body_template.format(**values)


async def users_with_roles(session: AsyncSession, tenant_id: uuid.UUID | None, role_codes: set[str]) -> list[User]:
    result = await session.execute(
        select(User)
        .join(Role, User.role_id == Role.id)
        .where(
            User.tenant_id == tenant_id,
            User.is_active.is_(True),
            Role.tenant_id == tenant_id,
            Role.code.in_(role_codes),
        )
    )
    return [user for user in result.scalars().all() if isinstance(user, User)]


def unique_recipients(users: list[User], exclude_user_id: uuid.UUID | None = None) -> list[User]:
    seen: set[uuid.UUID] = set()
    recipients: list[User] = []
    for user in users:
        if user.id == exclude_user_id or user.id in seen:
            continue
        seen.add(user.id)
        recipients.append(user)
    return recipients


async def create_notification(
    session: AsyncSession,
    *,
    recipient: User,
    notification_type: NotificationType,
    issue: Issue,
) -> Notification:
    title, body = render_message(notification_type, issue, recipient.language)
    notification = Notification(
        tenant_id=recipient.tenant_id,
        recipient_id=recipient.id,
        type=notification_type,
        title=title,
        body=body,
        issue_id=issue.id,
        is_read=False,
    )
    session.add(notification)
    await session.flush()
    await push_notification(session, recipient, notification)
    return notification


async def push_notification(session: AsyncSession, recipient: User, notification: Notification) -> None:
    result = await session.execute(
        select(DeviceToken).where(
            DeviceToken.tenant_id == recipient.tenant_id,
            DeviceToken.user_id == recipient.id,
            DeviceToken.deleted_at.is_(None),
        )
    )
    tokens = list(result.scalars().all())
    invalid = await send_expo_push(
        [token.expo_push_token for token in tokens],
        title=notification.title,
        body=notification.body,
        data={
            "notification_id": str(notification.id),
            "issue_id": str(notification.issue_id) if notification.issue_id else None,
            "type": notification.type,
        },
    )
    if invalid:
        await session.execute(delete(DeviceToken).where(DeviceToken.expo_push_token.in_(invalid)))


async def notify_issue_assigned(session: AsyncSession, issue: Issue) -> None:
    recipient = issue.assigned_to
    if recipient is None and issue.assigned_to_id is not None:
        recipient = await session.get(User, issue.assigned_to_id)
    if recipient is not None:
        await create_notification(
            session, recipient=recipient, notification_type="issue_assigned", issue=issue
        )


async def notify_issue_returned(session: AsyncSession, issue: Issue) -> None:
    recipient = issue.assigned_to
    if recipient is None and issue.assigned_to_id is not None:
        recipient = await session.get(User, issue.assigned_to_id)
    if recipient is not None:
        await create_notification(
            session, recipient=recipient, notification_type="issue_returned", issue=issue
        )


async def notify_issue_completed(session: AsyncSession, issue: Issue) -> None:
    recipients = await users_with_roles(session, issue.tenant_id, {"INSPECTOR", "DISPATCHER"})
    for recipient in unique_recipients(recipients):
        await create_notification(
            session, recipient=recipient, notification_type="issue_completed", issue=issue
        )


async def notify_issue_overdue(session: AsyncSession, issue: Issue) -> None:
    recipients = await users_with_roles(session, issue.tenant_id, {"DISPATCHER"})
    assignee = issue.assigned_to
    if assignee is None and issue.assigned_to_id is not None:
        assignee = await session.get(User, issue.assigned_to_id)
    if assignee is not None:
        recipients.append(assignee)
    for recipient in unique_recipients(recipients):
        await create_notification(
            session, recipient=recipient, notification_type="issue_overdue", issue=issue
        )


async def notify_issue_comment(session: AsyncSession, issue: Issue, actor: User) -> None:
    recipients = [user for user in [issue.created_by, issue.assigned_to] if user is not None]
    for recipient in unique_recipients(recipients, exclude_user_id=actor.id):
        await create_notification(
            session, recipient=recipient, notification_type="issue_comment", issue=issue
        )


async def list_notifications(
    session: AsyncSession,
    user: User,
    *,
    is_read: bool | None = None,
    cursor: str | None = None,
    limit: int = 30,
) -> tuple[list[Notification], str | None]:
    statement = select(Notification).where(
        Notification.tenant_id == user.tenant_id,
        Notification.recipient_id == user.id,
        Notification.deleted_at.is_(None),
    )
    if is_read is not None:
        statement = statement.where(Notification.is_read.is_(is_read))
    if cursor:
        created_raw, _, id_raw = cursor.partition("|")
        created_dt = datetime.fromisoformat(created_raw)
        if id_raw:
            statement = statement.where(
                or_(
                    Notification.created_at < created_dt,
                    and_(Notification.created_at == created_dt, Notification.id < uuid.UUID(id_raw)),
                )
            )
        else:
            statement = statement.where(Notification.created_at < created_dt)
    statement = statement.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit + 1)
    result = await session.execute(statement)
    items = list(result.scalars().all())
    next_cursor = None
    if len(items) > limit:
        last = items[limit - 1]
        next_cursor = f"{last.created_at.isoformat()}|{last.id}"
        items = items[:limit]
    return items, next_cursor


async def unread_count(session: AsyncSession, user: User) -> int:
    result = await session.execute(
        select(func.count(Notification.id)).where(
            Notification.tenant_id == user.tenant_id,
            Notification.recipient_id == user.id,
            Notification.is_read.is_(False),
            Notification.deleted_at.is_(None),
        )
    )
    return int(result.scalar_one())


async def mark_read(session: AsyncSession, user: User, notification_id: uuid.UUID) -> Notification | None:
    notification = await session.get(Notification, notification_id)
    if (
        notification is None
        or notification.tenant_id != user.tenant_id
        or notification.recipient_id != user.id
        or notification.deleted_at is not None
    ):
        return None
    notification.is_read = True
    await session.commit()
    return notification


async def mark_all_read(session: AsyncSession, user: User) -> int:
    result = await session.execute(
        update(Notification)
        .where(
            Notification.tenant_id == user.tenant_id,
            Notification.recipient_id == user.id,
            Notification.is_read.is_(False),
            Notification.deleted_at.is_(None),
        )
        .values(is_read=True)
    )
    await session.commit()
    return int(result.rowcount or 0)


async def register_device(session: AsyncSession, user: User, expo_push_token: str, platform: str) -> DeviceToken:
    now = datetime.now(UTC)
    # The token is globally unique; whoever registers it becomes its sole owner, so the
    # row is always (re)bound to the authenticated user's tenant_id/user_id (SEC-12).
    result = await session.execute(select(DeviceToken).where(DeviceToken.expo_push_token == expo_push_token))
    device = result.scalar_one_or_none()
    if device is None:
        device = DeviceToken(
            tenant_id=user.tenant_id,
            user_id=user.id,
            expo_push_token=expo_push_token,
            platform=platform,
            last_seen_at=now,
        )
        session.add(device)
    else:
        device.tenant_id = user.tenant_id
        device.user_id = user.id
        device.platform = platform
        device.last_seen_at = now
        device.deleted_at = None
    await session.commit()
    return device


async def unregister_device(session: AsyncSession, user: User, expo_push_token: str) -> None:
    await session.execute(
        delete(DeviceToken).where(
            DeviceToken.tenant_id == user.tenant_id,
            DeviceToken.user_id == user.id,
            DeviceToken.expo_push_token == expo_push_token,
        )
    )
    await session.commit()
