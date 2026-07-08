from enum import StrEnum


class IssueStatus(StrEnum):
    """Жизненный цикл задачи (поручения) в UOTP v3.

    DRAFT              черновик (голос / неполные данные), ждёт подтверждения автора
    NEW               новая, не распределена (исполнитель не назначен)
    ASSIGNED          назначена, на исполнении
    REVIEW_CONTROLLER на проверке у контролёра («Проверить исполнение»)
    REVIEW_AUTHOR     на проверке у автора («для снятия с контроля»)
    CLOSED            снято с контроля (уходит в архив)
    ON_HOLD           приостановлена (таймер на паузе)
    """

    DRAFT = "DRAFT"
    NEW = "NEW"
    ASSIGNED = "ASSIGNED"
    REVIEW_CONTROLLER = "REVIEW_CONTROLLER"
    REVIEW_AUTHOR = "REVIEW_AUTHOR"
    CLOSED = "CLOSED"
    ON_HOLD = "ON_HOLD"


# Задача ещё в работе (не закрыта).
OPEN_STATUSES = frozenset(
    {
        IssueStatus.DRAFT,
        IssueStatus.NEW,
        IssueStatus.ASSIGNED,
        IssueStatus.REVIEW_CONTROLLER,
        IssueStatus.REVIEW_AUTHOR,
        IssueStatus.ON_HOLD,
    }
)
TERMINAL_STATUSES = frozenset({IssueStatus.CLOSED})
# Статусы, в которых имеет смысл считать и показывать просрочку срока.
OVERDUE_ELIGIBLE_STATUSES = frozenset(
    {
        IssueStatus.NEW,
        IssueStatus.ASSIGNED,
        IssueStatus.REVIEW_CONTROLLER,
        IssueStatus.REVIEW_AUTHOR,
    }
)


class TaskRole(StrEnum):
    """Роль пользователя в конкретной задаче (поверх должности)."""

    AUTHOR = "AUTHOR"
    EXECUTOR = "EXECUTOR"
    CO_EXECUTOR = "CO_EXECUTOR"
    CONTROLLER = "CONTROLLER"
    ADMIN = "ADMIN"  # системный override, не роль в задаче


class TaskImportance(StrEnum):
    """Важность для личного контроля руководителя."""

    NORMAL = "NORMAL"
    IMPORTANT = "IMPORTANT"
    URGENT = "URGENT"


class TaskType(StrEnum):
    TASK = "TASK"  # обычная задача (видят участники)
    EVENT = "EVENT"  # мероприятие (видят все прикреплённые)


class TaskSource(StrEnum):
    INTERNAL = "internal"  # внутреннее поручение
    CITIZEN = "citizen"  # обращение гражданина
    EVENT = "event"  # мероприятие
    VOICE = "voice"  # голосовой ввод


# Разрешённые переходы по роли в задаче.
# Автор и контролёр закрывают; исполнитель только отмечает «Сделал»; соисполнитель не переводит.
ALLOWED_TRANSITIONS: dict[TaskRole, set[tuple[IssueStatus, IssueStatus]]] = {
    TaskRole.AUTHOR: {
        (IssueStatus.DRAFT, IssueStatus.NEW),
        (IssueStatus.DRAFT, IssueStatus.ASSIGNED),
        (IssueStatus.NEW, IssueStatus.ASSIGNED),
        (IssueStatus.NEW, IssueStatus.ON_HOLD),
        (IssueStatus.ON_HOLD, IssueStatus.NEW),
        (IssueStatus.ASSIGNED, IssueStatus.ON_HOLD),
        (IssueStatus.ON_HOLD, IssueStatus.ASSIGNED),
        # Автор может снять с контроля даже пока задача у контролёра.
        (IssueStatus.REVIEW_CONTROLLER, IssueStatus.CLOSED),
        (IssueStatus.REVIEW_CONTROLLER, IssueStatus.ASSIGNED),  # вернуть на доработку
        (IssueStatus.REVIEW_AUTHOR, IssueStatus.CLOSED),  # снять с контроля
        (IssueStatus.REVIEW_AUTHOR, IssueStatus.ASSIGNED),  # вернуть на доработку
    },
    TaskRole.EXECUTOR: {
        # «Сделал»: если у задачи есть контролёр — к нему, иначе сразу автору.
        (IssueStatus.ASSIGNED, IssueStatus.REVIEW_CONTROLLER),
        (IssueStatus.ASSIGNED, IssueStatus.REVIEW_AUTHOR),
    },
    TaskRole.CONTROLLER: {
        (IssueStatus.REVIEW_CONTROLLER, IssueStatus.REVIEW_AUTHOR),  # передать автору
        (IssueStatus.REVIEW_CONTROLLER, IssueStatus.CLOSED),  # снять с контроля
        (IssueStatus.REVIEW_CONTROLLER, IssueStatus.ASSIGNED),  # «не принять» / на доработку
    },
}

# Любой переход, существующий хотя бы у одной роли (для ADMIN-override).
ALL_VALID_TRANSITIONS: set[tuple[IssueStatus, IssueStatus]] = {
    transition for transitions in ALLOWED_TRANSITIONS.values() for transition in transitions
}


def can_transition(role: str, from_status: str, to_status: str) -> bool:
    """Разрешён ли переход для роли в задаче.

    role — значение TaskRole (AUTHOR/EXECUTOR/CO_EXECUTOR/CONTROLLER) или ADMIN.
    ADMIN может выполнить любой валидный переход, но не произвольный «прыжок».
    Соисполнитель не переводит задачу. Неизвестный статус или роль — запрет.
    """
    try:
        transition = (IssueStatus(from_status), IssueStatus(to_status))
    except ValueError:
        return False
    try:
        task_role = TaskRole(role)
    except ValueError:
        return False
    if task_role is TaskRole.ADMIN:
        return transition in ALL_VALID_TRANSITIONS
    if task_role is TaskRole.CO_EXECUTOR:
        return False
    return transition in ALLOWED_TRANSITIONS.get(task_role, set())


def is_terminal(status: str) -> bool:
    return status in TERMINAL_STATUSES
