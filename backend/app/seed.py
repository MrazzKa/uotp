import asyncio
import random
from datetime import UTC, datetime, timedelta

from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from app.config import settings
from app.db import AsyncSessionLocal
from app.modules.catalog.models import Category, Department, District
from app.modules.issues.models import Issue, IssueAssignee, IssueAttachment, IssueHistory
from app.modules.issues.service import next_public_number
from app.modules.issues.state import IssueStatus
from app.modules.roles.models import Role
from app.modules.sla.service import apply_sla_deadlines, seed_default_sla_rules
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

DEPARTMENTS = [
    ("city_services", "Городские службы", "Қалалық қызметтер", "internal"),
    ("roads", "Отдел дорог", "Жол бөлімі", "internal"),
    ("lighting", "Служба освещения", "Жарықтандыру қызметі", "contractor"),
    ("sanitation", "Санитарная служба", "Санитарлық қызмет", "contractor"),
    ("parks", "Зеленое хозяйство", "Жасыл шаруашылық", "contractor"),
]

DISTRICTS = [
    ("center", "Центр", "Орталық"),
    ("bereke", "Береке", "Береке"),
    ("rabochiy", "Рабочий поселок", "Жұмысшы кенті"),
    ("podgora", "Подгора", "Подгора"),
]

DISTRICT_POLYGONS = {
    "center": [(69.105, 54.845), (69.165, 54.845), (69.165, 54.895), (69.105, 54.895)],
    "bereke": [(69.165, 54.845), (69.235, 54.845), (69.235, 54.900), (69.165, 54.900)],
    "rabochiy": [(69.075, 54.810), (69.145, 54.810), (69.145, 54.845), (69.075, 54.845)],
    "podgora": [(69.095, 54.895), (69.205, 54.895), (69.205, 54.930), (69.095, 54.930)],
}

CATEGORIES = [
    ("roads", "Дороги", "Жолдар", None, "HIGH", "roads", "road", "#2563eb"),
    ("road_pothole", "Яма на дороге", "Жолдағы шұңқыр", "roads", "HIGH", "roads", "circle", "#1d4ed8"),
    ("road_sign", "Дорожный знак", "Жол белгісі", "roads", "MEDIUM", "roads", "signpost", "#3b82f6"),
    ("lighting", "Освещение", "Жарықтандыру", None, "MEDIUM", "lighting", "lamp", "#f59e0b"),
    ("lamp_broken", "Не работает фонарь", "Шам істемейді", "lighting", "MEDIUM", "lighting", "lightbulb", "#d97706"),
    ("sanitation", "Санитария", "Санитария", None, "MEDIUM", "sanitation", "trash", "#059669"),
    ("trash_overflow", "Переполненный контейнер", "Толған контейнер", "sanitation", "HIGH", "sanitation", "trash-2", "#047857"),
    ("parks", "Благоустройство", "Абаттандыру", None, "LOW", "parks", "trees", "#16a34a"),
    ("tree_damage", "Поврежденное дерево", "Зақымдалған ағаш", "parks", "LOW", "parks", "tree", "#15803d"),
]

STATUS_POOL = [
    IssueStatus.NEW,
    IssueStatus.QUALIFICATION,
    IssueStatus.ASSIGNED,
    IssueStatus.ACCEPTED,
    IssueStatus.IN_PROGRESS,
    IssueStatus.COMPLETED,
    IssueStatus.INSPECTION,
    IssueStatus.CLOSED,
]


def multipolygon_wkt(points: list[tuple[float, float]]) -> WKTElement:
    closed = points + [points[0]]
    coords = ", ".join(f"{lon} {lat}" for lon, lat in closed)
    return WKTElement(f"MULTIPOLYGON((({coords})))", srid=4326)


def random_point_for_district(code: str) -> tuple[float, float]:
    points = DISTRICT_POLYGONS[code]
    min_lon = min(point[0] for point in points)
    max_lon = max(point[0] for point in points)
    min_lat = min(point[1] for point in points)
    max_lat = max(point[1] for point in points)
    return random.uniform(min_lat, max_lat), random.uniform(min_lon, max_lon)


def point_wkt(latitude: float, longitude: float) -> WKTElement:
    return WKTElement(f"POINT({longitude} {latitude})", srid=4326)


async def get_or_create_tenant(session) -> Tenant:
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
    return tenant


async def seed_roles_users(session, tenant: Tenant) -> dict[str, User]:
    users: dict[str, User] = {}
    for code, name_ru, name_kk in ROLES:
        role = (
            await session.execute(select(Role).where(Role.tenant_id == tenant.id, Role.code == code))
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
            user = User(
                tenant_id=tenant.id,
                full_name=name_ru,
                phone=None,
                email=email,
                password_hash=hash_password("demo123"),
                role_id=role.id,
                language="ru",
            )
            session.add(user)
            await session.flush()
        user.role = role
        user.tenant = tenant
        users[code] = user
    return users


async def seed_catalogs(session, tenant: Tenant) -> tuple[dict[str, Department], dict[str, District], dict[str, Category]]:
    departments = {}
    for code, name_ru, name_kk, type_ in DEPARTMENTS:
        department = (
            await session.execute(
                select(Department).where(Department.tenant_id == tenant.id, Department.name_ru == name_ru)
            )
        ).scalar_one_or_none()
        if department is None:
            department = Department(
                tenant_id=tenant.id,
                name_ru=name_ru,
                name_kk=name_kk,
                type=type_,
                contacts={"phone": "+7 7152 00 00 00"},
            )
            session.add(department)
            await session.flush()
        departments[code] = department

    districts = {}
    for code, name_ru, name_kk in DISTRICTS:
        district = (
            await session.execute(select(District).where(District.tenant_id == tenant.id, District.code == code))
        ).scalar_one_or_none()
        if district is None:
            district = District(tenant_id=tenant.id, code=code, name_ru=name_ru, name_kk=name_kk)
            session.add(district)
            await session.flush()
        district.geometry = multipolygon_wkt(DISTRICT_POLYGONS[code])
        districts[code] = district

    categories = {}
    for code, name_ru, name_kk, parent_code, priority, department_code, icon, color in CATEGORIES:
        category = (
            await session.execute(select(Category).where(Category.tenant_id == tenant.id, Category.code == code))
        ).scalar_one_or_none()
        if category is None:
            parent = categories.get(parent_code) if parent_code else None
            category = Category(
                tenant_id=tenant.id,
                code=code,
                name_ru=name_ru,
                name_kk=name_kk,
                parent_id=parent.id if parent else None,
                default_priority=priority,
                default_department_id=departments[department_code].id,
                icon=icon,
                color=color,
            )
            session.add(category)
            await session.flush()
        categories[code] = category
    return departments, districts, categories


def demo_title(category: Category, index: int) -> str:
    return f"{category.name_ru}: обращение #{index + 1}"


async def seed_issues(
    session,
    tenant: Tenant,
    users: dict[str, User],
    departments: dict[str, Department],
    districts: dict[str, District],
    categories: dict[str, Category],
) -> None:
    existing_count = (
        await session.execute(select(Issue).where(Issue.tenant_id == tenant.id).limit(1))
    ).scalar_one_or_none()
    if existing_count is not None:
        result = await session.execute(select(Issue).where(Issue.tenant_id == tenant.id, Issue.deleted_at.is_(None)))
        all_issues = result.scalars().all()
        district_items = list(districts.items())
        random.seed(84)
        for index, issue in enumerate(all_issues):
            code, district = district_items[index % len(district_items)]
            latitude, longitude = random_point_for_district(code)
            issue.latitude = latitude
            issue.longitude = longitude
            issue.geometry = point_wkt(latitude, longitude)
            issue.district_id = district.id
            await apply_sla_deadlines(session, issue, base_time=issue.created_at, include_inspection=True)
            issue.is_overdue = bool(
                issue.sla_due_at
                and issue.sla_due_at < datetime.now(UTC)
                and issue.status not in {IssueStatus.CLOSED, IssueStatus.REJECTED, IssueStatus.DUPLICATE}
            )
        return

    executor = users["EXECUTOR"]
    dispatcher = users["DISPATCHER"]
    category_values = [category for category in categories.values() if category.parent_id is not None]
    department_values = list(departments.values())
    random.seed(42)

    for index in range(72):
        category = random.choice(category_values)
        district_code, district = random.choice(list(districts.items()))
        department = random.choice(department_values)
        status_value = random.choice(STATUS_POOL)
        created_at = datetime.now(UTC) - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
        public_number = await next_public_number(session, tenant.id, tenant.code)
        latitude, longitude = random_point_for_district(district_code)
        issue = Issue(
            tenant_id=tenant.id,
            public_number=public_number,
            source=random.choice(["app", "portal"]),
            title=demo_title(category, index),
            description="Демо-описание городской задачи для проверки списка, карточки и маршрута исполнения.",
            primary_category_id=category.id,
            tags=[category.code],
            status=status_value,
            priority=category.default_priority,
            address=f"Петропавловск, участок {index + 1}",
            latitude=latitude,
            longitude=longitude,
            geometry=point_wkt(latitude, longitude),
            district_id=district.id,
            created_by_id=dispatcher.id,
            assigned_to_id=executor.id if status_value not in {IssueStatus.NEW, IssueStatus.QUALIFICATION} else None,
            department_id=department.id,
            is_overdue=index % 11 == 0,
            created_at=created_at,
            updated_at=created_at,
        )
        session.add(issue)
        await session.flush()
        await apply_sla_deadlines(session, issue, base_time=created_at, include_inspection=True)
        issue.is_overdue = bool(
            issue.sla_due_at
            and issue.sla_due_at < datetime.now(UTC)
            and issue.status not in {IssueStatus.CLOSED, IssueStatus.REJECTED, IssueStatus.DUPLICATE}
        )
        session.add(
            IssueHistory(
                tenant_id=tenant.id,
                issue_id=issue.id,
                actor_id=dispatcher.id,
                action="created",
                to_status=IssueStatus.NEW,
                payload={"seed": True},
                created_at=created_at,
            )
        )
        if issue.assigned_to_id:
            session.add(
                IssueAssignee(
                    tenant_id=tenant.id,
                    issue_id=issue.id,
                    user_id=executor.id,
                    is_primary=True,
                )
            )
        if index % 3 == 0:
            session.add(
                IssueAttachment(
                    tenant_id=tenant.id,
                    issue_id=issue.id,
                    uploaded_by_id=dispatcher.id,
                    file_url=f"https://placehold.co/1200x800?text={public_number}",
                    medium_url=f"https://placehold.co/800x533?text={public_number}",
                    thumbnail_url=f"https://placehold.co/320x213?text={public_number}",
                    attachment_type="before",
                    mime_type="image/png",
                    size_bytes=1024,
                    antifraud_flags={},
                )
            )


async def seed() -> None:
    if settings.app_env not in {"dev", "demo"}:
        raise SystemExit("Seed is allowed only when APP_ENV is dev or demo.")
    async with AsyncSessionLocal() as session:
        tenant = await get_or_create_tenant(session)
        users = await seed_roles_users(session, tenant)
        departments, districts, categories = await seed_catalogs(session, tenant)
        await seed_default_sla_rules(session, tenant.id)
        await session.flush()
        await seed_issues(session, tenant, users, departments, districts, categories)
        await session.commit()
    print("Demo tenant, roles, users, catalogs and issues are ready.")


if __name__ == "__main__":
    asyncio.run(seed())
