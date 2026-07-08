"""Демонстрационный сид Кызылжарского района (UOTP v3).

Данные примерные и легко удаляемые: всё привязано к тенанту с кодом ``kyzylzhar``.
Моделируем уровни управления района (аким, замы, аппарат, отделы, сельские округа,
подрядные организации), а не конкретные штатные единицы. Реальные ФИО вносятся при внедрении.
Снести демо-данные: python -m app.seed wipe.
"""
import asyncio
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update

from app.config import settings
from app.db import AsyncSessionLocal
from app.modules.catalog.models import Category, Department, District, Sphere
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
from app.modules.issues.service import default_due_at, next_public_number
from app.modules.issues.state import IssueStatus
from app.modules.notifications.models import DeviceToken, Notification
from app.modules.roles.models import Role
from app.modules.sla.models import SlaRule
from app.modules.tenants.models import Tenant
from app.modules.users.models import User
from app.security import hash_password

TENANT_CODE = "kyzylzhar"

ROLES = [
    ("ADMIN", "Администратор", "Әкімші"),
    ("AKIM", "Аким района", "Аудан әкімі"),
    ("DEPUTY", "Заместитель акима", "Аким орынбасары"),
    ("APPARAT", "Руководитель аппарата", "Аппарат басшысы"),
    ("DEPT_HEAD", "Руководитель отдела", "Бөлім басшысы"),
    ("AKIM_SO", "Аким сельского округа", "Ауылдық округ әкімі"),
    ("SPECIALIST", "Главный специалист", "Бас маман"),
    ("OPERATOR", "Оператор", "Оператор"),
    ("CONTRACTOR", "Руководитель подрядной организации", "Мердігер ұйым басшысы"),
]

# Открытый справочник сфер (по названиям районных отделов).
SPHERES = [
    ("econ", "Экономика и финансы", "Экономика және қаржы", "chart", "#2563eb"),
    ("agro", "Сельское хозяйство и земельные отношения", "Ауыл шаруашылығы және жер қатынастары", "wheat", "#65a30d"),
    ("gkh", "ЖКХ, транспорт и дороги", "ТКШ, көлік және жолдар", "bolt", "#f59e0b"),
    ("build", "Строительство и архитектура", "Құрылыс және сәулет", "building", "#0ea5e9"),
    ("edu", "Образование", "Білім беру", "book", "#7c3aed"),
    ("culture", "Культура, спорт и языки", "Мәдениет, спорт және тілдер", "music", "#db2777"),
    ("social", "Занятость и социальные программы", "Жұмыспен қамту және әлеуметтік бағдарламалар", "users", "#0891b2"),
    ("inpol", "Внутренняя политика", "Ішкі саясат", "flag", "#475569"),
    ("vet", "Ветеринария", "Ветеринария", "paw", "#16a34a"),
    ("business", "Предпринимательство", "Кәсіпкерлік", "store", "#ea580c"),
    ("emergency", "ЧС и оперативные вопросы", "ТЖ және жедел мәселелер", "shield", "#dc2626"),
    ("apparatus", "Аппарат и организационное", "Аппарат және ұйымдастыру", "briefcase", "#334155"),
]

# code, name_ru, name_kk, type, parent_code
# типы: apparatus, apparat_dept, district_dept, rural_okrug, contractor
DEPARTMENTS = [
    ("apparat", "Аппарат акима района", "Аудан әкімінің аппараты", "apparatus", None),
    ("org_dept", "Организационный отдел", "Ұйымдастыру бөлімі", "apparat_dept", "apparat"),
    ("control_dept", "Отдел контроля исполнения", "Орындауды бақылау бөлімі", "apparat_dept", "apparat"),
    ("dep_econ", "Отдел экономики и финансов", "Экономика және қаржы бөлімі", "district_dept", None),
    ("dep_agro", "Отдел сельского хозяйства и земельных отношений", "Ауыл шаруашылығы бөлімі", "district_dept", None),
    ("dep_gkh", "Отдел ЖКХ, транспорта и автодорог", "ТКШ бөлімі", "district_dept", None),
    ("dep_build", "Отдел строительства и архитектуры", "Құрылыс бөлімі", "district_dept", None),
    ("dep_edu", "Отдел образования", "Білім бөлімі", "district_dept", None),
    ("dep_culture", "Отдел культуры и спорта", "Мәдениет бөлімі", "district_dept", None),
    ("dep_social", "Отдел занятости и социальных программ", "Жұмыспен қамту бөлімі", "district_dept", None),
    ("dep_inpol", "Отдел внутренней политики", "Ішкі саясат бөлімі", "district_dept", None),
    ("dep_vet", "Отдел ветеринарии", "Ветеринария бөлімі", "district_dept", None),
    ("dep_business", "Отдел предпринимательства", "Кәсіпкерлік бөлімі", "district_dept", None),
    ("con_clean", "ТОО Бишкуль Тазалык", "Бішкүл Тазалық ЖШС", "contractor", None),
    ("con_road", "ТОО Дорстрой-Север", "Дорстрой-Север ЖШС", "contractor", None),
]

# 17 сельских округов Кызылжарского района (org-единицы типа rural_okrug)
RURAL_OKRUGS = [
    ("so_asanov", "Асановский сельский округ"),
    ("so_arhangel", "Архангельский сельский округ"),
    ("so_berezov", "Березовский сельский округ"),
    ("so_beskol", "Бескольский сельский округ"),
    ("so_bogolyub", "Боголюбовский сельский округ"),
    ("so_vagulin", "Вагулинский сельский округ"),
    ("so_vinograd", "Виноградовский сельский округ"),
    ("so_dolmatov", "Долматовский сельский округ"),
    ("so_kyzylzhar", "Кызылжарский сельский округ"),
    ("so_nalobin", "Налобинский сельский округ"),
    ("so_novonikol", "Новоникольский сельский округ"),
    ("so_peterfeld", "Петерфельдский сельский округ"),
    ("so_pribrezh", "Прибрежный сельский округ"),
    ("so_rassvet", "Рассветский сельский округ"),
    ("so_sokolov", "Соколовский сельский округ"),
    ("so_teplich", "Тепличный сельский округ"),
    ("so_yakor", "Якорьский сельский округ"),
]

# code, email, ФИО, роль, сфера, контролирует все сферы, отдел/округ, должность
USERS = [
    ("admin", "admin@uotp.local", "Администратор системы", "ADMIN", None, False, None, "Администратор"),
    ("akim", "akim@uotp.local", "Бейбут Исманов", "AKIM", None, True, "apparat", "Аким Кызылжарского района"),
    ("deputy_apk", "deputy1@uotp.local", "Санат Аубакиров", "DEPUTY", "econ", True, "apparat", "Заместитель акима (АПК, экономика, финансы)"),
    ("deputy_social", "deputy2@uotp.local", "Азат Ибраев", "DEPUTY", "social", True, "apparat", "Заместитель акима (социальная сфера)"),
    ("deputy_oper", "deputy3@uotp.local", "Бактияр Бикенев", "DEPUTY", "gkh", True, "apparat", "Заместитель акима (оперативные вопросы, ЖКХ, ЧС)"),
    ("apparat", "apparat@uotp.local", "Гульнара Ахметова", "APPARAT", None, True, "apparat", "Руководитель аппарата"),
    ("operator", "operator@uotp.local", "Дмитрий Ким", "OPERATOR", None, False, "org_dept", "Оператор"),
    ("head_gkh", "head_gkh@uotp.local", "Асхат Нурланов", "DEPT_HEAD", "gkh", False, "dep_gkh", "Руководитель отдела ЖКХ"),
    ("head_edu", "head_edu@uotp.local", "Марина Ли", "DEPT_HEAD", "edu", False, "dep_edu", "Руководитель отдела образования"),
    ("head_agro", "head_agro@uotp.local", "Ерлан Досов", "DEPT_HEAD", "agro", False, "dep_agro", "Руководитель отдела сельского хозяйства"),
    ("spec_gkh", "spec_gkh@uotp.local", "Айгуль Сатпаева", "SPECIALIST", "gkh", False, "dep_gkh", "Главный специалист (ЖКХ)"),
    ("spec_road", "spec_road@uotp.local", "Нурбек Оспанов", "SPECIALIST", "gkh", False, "dep_gkh", "Главный специалист (дороги)"),
    ("spec_edu", "spec_edu@uotp.local", "Данияр Ахметов", "SPECIALIST", "edu", False, "dep_edu", "Главный специалист (образование)"),
    ("akim_beskol", "so_beskol@uotp.local", "Кайрат Смагулов", "AKIM_SO", None, False, "so_beskol", "Аким Бескольского с/о"),
    ("akim_sokolov", "so_sokolov@uotp.local", "Асель Жумаева", "AKIM_SO", None, False, "so_sokolov", "Аким Соколовского с/о"),
    ("akim_vinograd", "so_vinograd@uotp.local", "Виктор Петров", "AKIM_SO", None, False, "so_vinograd", "Аким Виноградовского с/о"),
    ("con_clean", "con_clean@uotp.local", "Олег Мельник", "CONTRACTOR", "gkh", False, "con_clean", "Руководитель ТОО Бишкуль Тазалык"),
    ("con_road", "con_road@uotp.local", "Тимур Идрисов", "CONTRACTOR", "gkh", False, "con_road", "Руководитель ТОО Дорстрой-Север"),
]

# заголовок, сфера, ключ исполнителя, важность, статус, на личном контроле акима, дней назад
TASKS = [
    ("Устранить яму на трассе при въезде в Бишкуль", "gkh", "con_road", "URGENT", IssueStatus.ASSIGNED, True, 1),
    ("Заменить перегоревшие фонари на центральной улице", "gkh", "spec_gkh", "IMPORTANT", IssueStatus.REVIEW_CONTROLLER, True, 2),
    ("Организовать вывоз мусора с несанкционированной свалки", "gkh", "con_clean", "URGENT", IssueStatus.ASSIGNED, True, 1),
    ("Подготовить справку по очереди в детские сады района", "social", "spec_edu", "IMPORTANT", IssueStatus.REVIEW_AUTHOR, True, 2),
    ("Проверить готовность школ к учебному году", "edu", "head_edu", "IMPORTANT", IssueStatus.ASSIGNED, False, 3),
    ("Составить план весенних полевых работ", "agro", "head_agro", "NORMAL", IssueStatus.NEW, False, 0),
    ("Отчитаться о благоустройстве Соколовского округа", "gkh", "akim_sokolov", "NORMAL", IssueStatus.ASSIGNED, False, 2),
    ("Проверить состояние водопровода в Бескольском округе", "gkh", "akim_beskol", "URGENT", IssueStatus.ASSIGNED, True, 4),
    ("Подготовить данные по занятости за квартал", "social", "spec_edu", "NORMAL", IssueStatus.CLOSED, False, 9),
    ("Восстановить дорожный знак на повороте к трассе", "gkh", "spec_road", "NORMAL", IssueStatus.REVIEW_CONTROLLER, False, 3),
    ("Организовать субботник в Виноградовском округе", "gkh", "akim_vinograd", "NORMAL", IssueStatus.ASSIGNED, False, 2),
    ("Собрать сведения по поголовью скота", "vet", "head_agro", "NORMAL", IssueStatus.ON_HOLD, False, 6),
    ("Подготовить отчёт по обращениям граждан за месяц", "apparatus", "operator", "NORMAL", IssueStatus.CLOSED, False, 12),
    ("Проверить освещение возле школы в Бескольском округе", "gkh", "akim_beskol", "IMPORTANT", IssueStatus.REVIEW_CONTROLLER, True, 3),
]


async def get_or_create_tenant(session) -> Tenant:
    tenant = (
        await session.execute(select(Tenant).where(Tenant.code == TENANT_CODE))
    ).scalar_one_or_none()
    if tenant is None:
        tenant = Tenant(
            code=TENANT_CODE,
            name_ru="Кызылжарский район",
            name_kk="Қызылжар ауданы",
            subdomain=TENANT_CODE,
            timezone="Asia/Almaty",
            locale_default="ru",
            tenant_id=None,
        )
        session.add(tenant)
        await session.flush()
        tenant.tenant_id = tenant.id
    return tenant


async def seed_reference(session, tenant: Tenant):
    roles: dict[str, Role] = {}
    for code, ru, kk in ROLES:
        role = (
            await session.execute(select(Role).where(Role.tenant_id == tenant.id, Role.code == code))
        ).scalar_one_or_none()
        if role is None:
            role = Role(tenant_id=tenant.id, code=code, name_ru=ru, name_kk=kk, permissions={}, is_system=True)
            session.add(role)
            await session.flush()
        roles[code] = role

    spheres: dict[str, Sphere] = {}
    for code, ru, kk, icon, color in SPHERES:
        sphere = (
            await session.execute(select(Sphere).where(Sphere.tenant_id == tenant.id, Sphere.code == code))
        ).scalar_one_or_none()
        if sphere is None:
            sphere = Sphere(tenant_id=tenant.id, code=code, name_ru=ru, name_kk=kk, icon=icon, color=color)
            session.add(sphere)
            await session.flush()
        spheres[code] = sphere

    departments: dict[str, Department] = {}
    for code, ru, kk, type_, parent_code in DEPARTMENTS:
        dept = (
            await session.execute(
                select(Department).where(Department.tenant_id == tenant.id, Department.name_ru == ru)
            )
        ).scalar_one_or_none()
        if dept is None:
            dept = Department(
                tenant_id=tenant.id, name_ru=ru, name_kk=kk, type=type_,
                parent_id=departments[parent_code].id if parent_code else None, contacts={},
            )
            session.add(dept)
            await session.flush()
        departments[code] = dept
    # 17 сельских округов как орг-единицы
    for code, ru in RURAL_OKRUGS:
        dept = (
            await session.execute(
                select(Department).where(Department.tenant_id == tenant.id, Department.name_ru == ru)
            )
        ).scalar_one_or_none()
        if dept is None:
            dept = Department(tenant_id=tenant.id, name_ru=ru, name_kk=ru, type="rural_okrug", contacts={})
            session.add(dept)
            await session.flush()
        departments[code] = dept
    return roles, spheres, departments


async def seed_users(session, tenant, roles, spheres, departments) -> dict[str, User]:
    users: dict[str, User] = {}
    for code, email, full_name, role_code, sphere_code, controls_all, dept_code, position in USERS:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if user is None:
            user = User(
                tenant_id=tenant.id, full_name=full_name, email=email,
                password_hash=hash_password("demo123"), role_id=roles[role_code].id, language="ru",
                position_title=position,
                sphere_id=spheres[sphere_code].id if sphere_code else None,
                controls_all_spheres=controls_all,
                department_id=departments[dept_code].id if dept_code else None,
            )
            session.add(user)
            await session.flush()
        users[code] = user
    return users


async def seed_tasks(session, tenant, spheres, users) -> None:
    existing = (
        await session.execute(select(Issue).where(Issue.tenant_id == tenant.id).limit(1))
    ).scalar_one_or_none()
    if existing is not None:
        return
    now = datetime.now(UTC)
    for index, (title, sphere_code, executor_key, importance, status_value, personal, days_ago) in enumerate(TASKS):
        created_at = now - timedelta(days=days_ago, hours=index)
        author = users["akim"] if personal else users["apparat"]
        controller = users["head_gkh"] if sphere_code == "gkh" else users["apparat"]
        executor = users[executor_key]
        due_at = default_due_at(importance, created_at)
        public_number = await next_public_number(session, tenant.id, tenant.code)
        assigned = status_value not in {IssueStatus.NEW, IssueStatus.DRAFT}
        paused = status_value == IssueStatus.ON_HOLD
        is_overdue = bool(
            due_at < now
            and status_value in {IssueStatus.NEW, IssueStatus.ASSIGNED, IssueStatus.REVIEW_CONTROLLER, IssueStatus.REVIEW_AUTHOR}
            and not paused
        )
        issue = Issue(
            tenant_id=tenant.id, public_number=public_number, source="internal", task_type="TASK",
            title=title, description=title, tags=[sphere_code], status=status_value, priority="MEDIUM",
            importance=importance, sphere_id=spheres[sphere_code].id,
            controller_id=controller.id if assigned else None, due_at=due_at, sla_due_at=due_at,
            created_by_id=author.id, assigned_to_id=executor.id if assigned else None,
            is_overdue=is_overdue, sla_paused_at=created_at if paused else None,
            closed_at=(created_at + timedelta(hours=2)) if status_value == IssueStatus.CLOSED else None,
            created_at=created_at, updated_at=created_at,
        )
        session.add(issue)
        await session.flush()
        if assigned:
            session.add(
                IssueAssignee(tenant_id=tenant.id, issue_id=issue.id, user_id=executor.id, is_primary=True, role="EXECUTOR")
            )
        session.add(
            IssueHistory(
                tenant_id=tenant.id, issue_id=issue.id, actor_id=author.id, action="created",
                to_status=IssueStatus.NEW, payload={"seed": True}, created_at=created_at,
            )
        )
        if personal:
            session.add(
                IssuePersonalMark(tenant_id=tenant.id, issue_id=issue.id, user_id=users["akim"].id, importance=importance)
            )


async def seed() -> None:
    if settings.app_env not in {"dev", "demo"}:
        raise SystemExit("Seed is allowed only when APP_ENV is dev or demo.")
    async with AsyncSessionLocal() as session:
        tenant = await get_or_create_tenant(session)
        roles, spheres, departments = await seed_reference(session, tenant)
        users = await seed_users(session, tenant, roles, spheres, departments)
        await session.flush()
        # Закрепляем контролёров за сферами. Один контролёр может вести несколько сфер.
        sphere_controllers = {
            "gkh": "head_gkh", "edu": "head_edu", "agro": "head_agro", "vet": "head_agro",
            "social": "deputy_social", "econ": "deputy_apk", "business": "deputy_apk",
            "build": "deputy_oper", "emergency": "deputy_oper",
            "apparatus": "apparat", "culture": "apparat", "inpol": "apparat",
        }
        for sphere_code, user_key in sphere_controllers.items():
            sphere = spheres.get(sphere_code)
            controller = users.get(user_key)
            if sphere is not None and controller is not None:
                sphere.controller_id = controller.id
        await session.flush()
        await seed_tasks(session, tenant, spheres, users)
        await session.commit()
    print(f"Demo tenant '{TENANT_CODE}' (Кызылжарский район): roles, spheres, org units, users and tasks are ready.")


async def wipe() -> None:
    """Полностью удалить демо-данные тенанта (для внесения реальных данных)."""
    async with AsyncSessionLocal() as session:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.code == TENANT_CODE))
        ).scalar_one_or_none()
        if tenant is None:
            print("Nothing to wipe.")
            return
        tid = tenant.id
        # Сфера ссылается на пользователя (контролёр), а пользователь на сферу: разрываем цикл.
        await session.execute(update(Sphere).where(Sphere.tenant_id == tid).values(controller_id=None))
        # audit_log НЕ трогаем: он append-only (защищён триггером) и хранится постоянно.
        # Полный переход демо -> реальные данные делается сбросом схемы (см. docs/DEPLOY.md).
        for model in (
            ExifData, IssueAttachment, IssueComment, Notification, IssuePersonalMark,
            IssueAssignee, IssueHistory, DeviceToken, Issue,
            SlaRule, Category, District, IssueNumberCounter,
            User, Department, Sphere, Role, Tenant,
        ):
            await session.execute(delete(model).where(model.tenant_id == tid))
        await session.commit()
    print(f"Demo tenant '{TENANT_CODE}' wiped.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "wipe":
        asyncio.run(wipe())
    else:
        asyncio.run(seed())
