from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.roles.models import Role


async def get_role_by_code(session: AsyncSession, tenant_id, code: str) -> Role | None:
    result = await session.execute(
        select(Role).where(Role.tenant_id == tenant_id, Role.code == code, Role.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()
