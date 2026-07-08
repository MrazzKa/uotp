from app.modules.issues.state import IssueStatus, TaskRole, can_transition


def test_executor_marks_done_to_controller_review() -> None:
    assert can_transition(TaskRole.EXECUTOR, IssueStatus.ASSIGNED, IssueStatus.REVIEW_CONTROLLER)


def test_executor_marks_done_to_author_when_no_controller() -> None:
    assert can_transition(TaskRole.EXECUTOR, IssueStatus.ASSIGNED, IssueStatus.REVIEW_AUTHOR)


def test_executor_cannot_close() -> None:
    # Исполнитель не закрывает задачу, только отмечает «Сделал».
    assert not can_transition(TaskRole.EXECUTOR, IssueStatus.ASSIGNED, IssueStatus.CLOSED)
    assert not can_transition(TaskRole.EXECUTOR, IssueStatus.REVIEW_AUTHOR, IssueStatus.CLOSED)


def test_controller_closes_returns_or_hands_to_author() -> None:
    assert can_transition(TaskRole.CONTROLLER, IssueStatus.REVIEW_CONTROLLER, IssueStatus.CLOSED)
    assert can_transition(TaskRole.CONTROLLER, IssueStatus.REVIEW_CONTROLLER, IssueStatus.ASSIGNED)
    assert can_transition(TaskRole.CONTROLLER, IssueStatus.REVIEW_CONTROLLER, IssueStatus.REVIEW_AUTHOR)


def test_author_closes_from_author_review() -> None:
    assert can_transition(TaskRole.AUTHOR, IssueStatus.REVIEW_AUTHOR, IssueStatus.CLOSED)


def test_author_can_close_even_at_controller_review() -> None:
    assert can_transition(TaskRole.AUTHOR, IssueStatus.REVIEW_CONTROLLER, IssueStatus.CLOSED)


def test_author_distributes_new_to_assigned() -> None:
    assert can_transition(TaskRole.AUTHOR, IssueStatus.NEW, IssueStatus.ASSIGNED)


def test_author_confirms_draft() -> None:
    assert can_transition(TaskRole.AUTHOR, IssueStatus.DRAFT, IssueStatus.ASSIGNED)
    assert can_transition(TaskRole.AUTHOR, IssueStatus.DRAFT, IssueStatus.NEW)


def test_co_executor_cannot_transition() -> None:
    assert not can_transition(TaskRole.CO_EXECUTOR, IssueStatus.ASSIGNED, IssueStatus.REVIEW_AUTHOR)
    assert not can_transition(TaskRole.CO_EXECUTOR, IssueStatus.REVIEW_AUTHOR, IssueStatus.CLOSED)


def test_admin_override_valid_only() -> None:
    assert can_transition(TaskRole.ADMIN, IssueStatus.REVIEW_CONTROLLER, IssueStatus.CLOSED)
    assert not can_transition(TaskRole.ADMIN, IssueStatus.NEW, IssueStatus.CLOSED)
    assert not can_transition(TaskRole.ADMIN, IssueStatus.DRAFT, IssueStatus.CLOSED)


def test_unknown_status_or_role_is_rejected() -> None:
    assert not can_transition(TaskRole.AUTHOR, "QUALIFICATION", "CLOSED")
    assert not can_transition("SOMETHING", IssueStatus.NEW, IssueStatus.ASSIGNED)
