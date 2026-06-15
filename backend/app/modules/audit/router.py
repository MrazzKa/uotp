from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_roles
from app.modules.audit.schemas import AuditLogRead
from app.modules.audit.service import list_audit_log
from app.modules.users.models import User

router = APIRouter(prefix="/admin/audit-log", tags=["admin-audit"])


@router.get("", response_model=list[AuditLogRead])
async def list_audit_log_endpoint(
    current_user: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_session)],
    action: str | None = None,
    entity_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    return await list_audit_log(
        session, current_user.tenant_id, action=action, entity_id=entity_id, limit=limit
    )
