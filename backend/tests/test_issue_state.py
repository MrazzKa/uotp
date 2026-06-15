from app.modules.issues.state import can_transition


def test_executor_cannot_close_issue() -> None:
    assert not can_transition("EXECUTOR", "IN_PROGRESS", "CLOSED")


def test_executor_can_complete_in_progress_issue() -> None:
    assert can_transition("EXECUTOR", "IN_PROGRESS", "COMPLETED")


def test_admin_can_override_valid_role_transitions() -> None:
    # ADMIN may cross role boundaries on legitimate workflow transitions...
    assert can_transition("ADMIN", "COMPLETED", "INSPECTION")
    assert can_transition("ADMIN", "NEW", "QUALIFICATION")


def test_admin_cannot_make_nonsensical_jumps() -> None:
    # ...but not arbitrary jumps that exist in no role's matrix.
    assert not can_transition("ADMIN", "NEW", "CLOSED")
    assert not can_transition("ADMIN", "NEW", "IN_PROGRESS")


def test_akim_is_read_only() -> None:
    assert not can_transition("AKIM", "NEW", "QUALIFICATION")
    assert not can_transition("AKIM", "COMPLETED", "INSPECTION")
