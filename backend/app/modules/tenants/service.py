from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tenants.models import Tenant


async def get_tenant_by_code(session: AsyncSession, code: str) -> Tenant | None:
    result = await session.execute(select(Tenant).where(Tenant.code == code, Tenant.deleted_at.is_(None)))
    return result.scalar_one_or_none()
