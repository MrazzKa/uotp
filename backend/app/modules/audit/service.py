import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.modules.users.models import User


async def log_audit(
    session: AsyncSession,
    actor: User,
    action: str,
    entity_type: str,
    *,
    entity_id: uuid.UUID | None = None,
    context: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Append an audit entry to the current transaction (caller commits)."""
    entry = AuditLog(
        tenant_id=actor.tenant_id,
        actor_id=actor.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip_address,
        context=context or {},
    )
    session.add(entry)
    return entry


async def list_audit_log(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    action: str | None = None,
    entity_id: uuid.UUID | None = None,
    limit: int = 100,
) -> list[AuditLog]:
    statement = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
    if action:
        statement = statement.where(AuditLog.action == action)
    if entity_id:
        statement = statement.where(AuditLog.entity_id == entity_id)
    statement = statement.order_by(AuditLog.created_at.desc()).limit(limit)
    result = await session.execute(statement)
    return list(result.scalars().all())
