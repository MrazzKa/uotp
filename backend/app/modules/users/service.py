from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User


async def get_user_by_login(session: AsyncSession, login: str) -> User | None:
    result = await session.execute(
        select(User).where(
            or_(User.email == login, User.phone == login),
            User.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()
