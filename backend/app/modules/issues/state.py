from enum import StrEnum


class IssueStatus(StrEnum):
    NEW = "NEW"
    QUALIFICATION = "QUALIFICATION"
    ASSIGNED = "ASSIGNED"
    ACCEPTED = "ACCEPTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    INSPECTION = "INSPECTION"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"
    RETURNED = "RETURNED"
    DUPLICATE = "DUPLICATE"


class IssuePriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IssueSource(StrEnum):
    APP = "app"
    PORTAL = "portal"
    SYSTEM = "system"


ALLOWED_TRANSITIONS: dict[str, set[tuple[IssueStatus, IssueStatus]]] = {
    "DISPATCHER": {
        (IssueStatus.NEW, IssueStatus.QUALIFICATION),
        (IssueStatus.NEW, IssueStatus.REJECTED),
        (IssueStatus.QUALIFICATION, IssueStatus.ASSIGNED),
        (IssueStatus.QUALIFICATION, IssueStatus.REJECTED),
        (IssueStatus.ASSIGNED, IssueStatus.ASSIGNED),
    },
    "EXECUTOR": {
        (IssueStatus.ASSIGNED, IssueStatus.ACCEPTED),
        (IssueStatus.ACCEPTED, IssueStatus.IN_PROGRESS),
        (IssueStatus.IN_PROGRESS, IssueStatus.COMPLETED),
    },
    "INSPECTOR": {
        (IssueStatus.COMPLETED, IssueStatus.INSPECTION),
        (IssueStatus.INSPECTION, IssueStatus.CLOSED),
        (IssueStatus.INSPECTION, IssueStatus.RETURNED),
    },
}


# Every transition that exists in any role's matrix. ADMIN may perform any of
# these (override across roles) but not arbitrary/nonsensical jumps (e.g. NEW->CLOSED).
ALL_VALID_TRANSITIONS: set[tuple[IssueStatus, IssueStatus]] = {
    transition for transitions in ALLOWED_TRANSITIONS.values() for transition in transitions
}


def can_transition(role: str, from_status: str, to_status: str) -> bool:
    if role == "AKIM":
        return False
    try:
        transition = (IssueStatus(from_status), IssueStatus(to_status))
    except ValueError:
        return False
    if role == "ADMIN":
        return transition in ALL_VALID_TRANSITIONS
    return transition in ALLOWED_TRANSITIONS.get(role, set())
