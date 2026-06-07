import asyncio

from sqlalchemy import select

from app.config import settings
from app.db import AsyncSessionLocal
from app.modules.roles.models import Role
from app.modules.tenants.models import Tenant
from app.modules.users.models import User
from app.security import hash_password

ROLES = [
    ("ADMIN", "Администратор", "Әкімші"),
    ("DISPATCHER", "Диспетчер", "Диспетчер"),
    ("EXECUTOR", "Исполнитель", "Орындаушы"),
    ("AKIM", "Аким", "Әкім"),
    ("INSPECTOR", "Инспектор", "Инспектор"),
]


async def seed() -> None:
    if settings.app_env not in {"dev", "demo"}:
        raise SystemExit("Seed is allowed only when APP_ENV is dev or demo.")
    async with AsyncSessionLocal() as session:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.code == "petropavlovsk"))
        ).scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(
                code="petropavlovsk",
                name_ru="Петропавловск",
                name_kk="Петропавл",
                subdomain="petropavlovsk",
                timezone="Asia/Qyzylorda",
                locale_default="ru",
                tenant_id=None,
            )
            session.add(tenant)
            await session.flush()
            tenant.tenant_id = tenant.id

        for code, name_ru, name_kk in ROLES:
            role = (
                await session.execute(
                    select(Role).where(Role.tenant_id == tenant.id, Role.code == code)
                )
            ).scalar_one_or_none()
            if role is None:
                role = Role(
                    tenant_id=tenant.id,
                    code=code,
                    name_ru=name_ru,
                    name_kk=name_kk,
                    permissions={},
                    is_system=True,
                )
                session.add(role)
                await session.flush()
            email = f"{code.lower()}@uotp.local"
            user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if user is None:
                session.add(
                    User(
                        tenant_id=tenant.id,
                        full_name=name_ru,
                        phone=None,
                        email=email,
                        password_hash=hash_password("demo123"),
                        role_id=role.id,
                        language="ru",
                    )
                )
        await session.commit()
    print("Demo tenant, roles and users are ready.")


if __name__ == "__main__":
    asyncio.run(seed())
