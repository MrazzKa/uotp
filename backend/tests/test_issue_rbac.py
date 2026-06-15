from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.modules.issues.service import ensure_can_create_issue, ensure_can_write


def _actor(role: str):
    return SimpleNamespace(role=SimpleNamespace(code=role), id="u", tenant_id="t")


@pytest.mark.parametrize("role", ["ADMIN", "DISPATCHER"])
def test_admin_and_dispatcher_can_create_from_any_source(role: str) -> None:
    ensure_can_create_issue(_actor(role), "portal")
    ensure_can_create_issue(_actor(role), "app")


def test_executor_can_create_only_from_app() -> None:
    ensure_can_create_issue(_actor("EXECUTOR"), "app")
    with pytest.raises(HTTPException) as exc:
        ensure_can_create_issue(_actor("EXECUTOR"), "portal")
    assert exc.value.status_code == 403


@pytest.mark.parametrize("role", ["AKIM", "INSPECTOR"])
def test_akim_and_inspector_cannot_create(role: str) -> None:
    with pytest.raises(HTTPException) as exc:
        ensure_can_create_issue(_actor(role), "app")
    assert exc.value.status_code == 403


def test_akim_blocked_from_any_write() -> None:
    with pytest.raises(HTTPException) as exc:
        ensure_can_write(_actor("AKIM"))
    assert exc.value.status_code == 403


@pytest.mark.parametrize("role", ["ADMIN", "DISPATCHER", "EXECUTOR", "INSPECTOR"])
def test_non_readonly_roles_can_write(role: str) -> None:
    ensure_can_write(_actor(role))  # should not raise
