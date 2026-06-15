from uuid import uuid4

from app.modules.dashboard.service import visible_issue_ids_statement
from app.modules.roles.models import Role
from app.modules.users.models import User


def test_dashboard_visibility_for_executor_filters_by_assignee() -> None:
    user = User(id=uuid4(), tenant_id=uuid4())
    user.role = Role(code="EXECUTOR")

    compiled = str(visible_issue_ids_statement(user).compile(compile_kwargs={"literal_binds": True}))

    assert "issue_assignees" in compiled
    assert "assigned_to_id" in compiled


def test_dashboard_visibility_for_admin_keeps_tenant_scope_only() -> None:
    user = User(id=uuid4(), tenant_id=uuid4())
    user.role = Role(code="ADMIN")

    compiled = str(visible_issue_ids_statement(user).compile(compile_kwargs={"literal_binds": True}))

    assert "issue_assignees" not in compiled
    assert "tenant_id" in compiled
