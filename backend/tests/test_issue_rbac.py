from types import SimpleNamespace

from app.modules.issues.service import can_user_transition, task_roles_for
from app.modules.issues.state import IssueStatus, TaskRole


def _user(uid: str, role: str = "SPECIALIST"):
    return SimpleNamespace(id=uid, role=SimpleNamespace(code=role))


def _assignee(uid: str, role: str = "EXECUTOR"):
    return SimpleNamespace(user_id=uid, role=role)


def _issue(status, created_by, controller=None, assignees=()):
    return SimpleNamespace(
        status=status,
        created_by_id=created_by,
        controller_id=controller,
        assignees=list(assignees),
    )


def test_author_role_detected() -> None:
    issue = _issue(IssueStatus.NEW, created_by="a")
    assert TaskRole.AUTHOR in task_roles_for(issue, _user("a"))


def test_executor_and_co_executor_roles() -> None:
    issue = _issue(
        IssueStatus.ASSIGNED,
        created_by="a",
        assignees=[_assignee("e", "EXECUTOR"), _assignee("c", "CO_EXECUTOR")],
    )
    assert TaskRole.EXECUTOR in task_roles_for(issue, _user("e"))
    assert TaskRole.CO_EXECUTOR in task_roles_for(issue, _user("c"))


def test_controller_role_detected() -> None:
    issue = _issue(IssueStatus.REVIEW_CONTROLLER, created_by="a", controller="k")
    assert TaskRole.CONTROLLER in task_roles_for(issue, _user("k"))


def test_executor_can_submit_but_not_close() -> None:
    issue = _issue(IssueStatus.ASSIGNED, created_by="a", controller="k", assignees=[_assignee("e")])
    assert can_user_transition(issue, _user("e"), IssueStatus.REVIEW_CONTROLLER)
    assert not can_user_transition(issue, _user("e"), IssueStatus.CLOSED)


def test_co_executor_cannot_transition() -> None:
    issue = _issue(IssueStatus.ASSIGNED, created_by="a", assignees=[_assignee("c", "CO_EXECUTOR")])
    assert not can_user_transition(issue, _user("c"), IssueStatus.REVIEW_AUTHOR)


def test_controller_can_close() -> None:
    issue = _issue(IssueStatus.REVIEW_CONTROLLER, created_by="a", controller="k")
    assert can_user_transition(issue, _user("k"), IssueStatus.CLOSED)


def test_author_can_close_and_distribute() -> None:
    review = _issue(IssueStatus.REVIEW_AUTHOR, created_by="a")
    assert can_user_transition(review, _user("a"), IssueStatus.CLOSED)
    new = _issue(IssueStatus.NEW, created_by="a")
    assert can_user_transition(new, _user("a"), IssueStatus.ASSIGNED)


def test_admin_from_system_role_overrides() -> None:
    issue = _issue(IssueStatus.REVIEW_CONTROLLER, created_by="a", controller="k")
    admin = _user("x", role="ADMIN")
    assert TaskRole.ADMIN in task_roles_for(issue, admin)
    assert can_user_transition(issue, admin, IssueStatus.CLOSED)


def test_uninvolved_user_has_no_roles() -> None:
    issue = _issue(IssueStatus.ASSIGNED, created_by="a", controller="k", assignees=[_assignee("e")])
    assert task_roles_for(issue, _user("z")) == set()
    assert not can_user_transition(issue, _user("z"), IssueStatus.CLOSED)
