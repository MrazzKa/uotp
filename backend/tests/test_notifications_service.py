import uuid
from types import SimpleNamespace

from app.modules.notifications.service import render_message, unique_recipients


def test_render_message_uses_user_language() -> None:
    issue = SimpleNamespace(public_number="PVL-2026-00001", title="Broken light")

    title, body = render_message("issue_assigned", issue, "kk")

    assert "PVL-2026-00001" in title
    assert "Broken light" in body


def test_unique_recipients_deduplicates_and_excludes_actor() -> None:
    actor_id = uuid.uuid4()
    user_id = uuid.uuid4()
    actor = SimpleNamespace(id=actor_id)
    user = SimpleNamespace(id=user_id)

    recipients = unique_recipients([actor, user, user], exclude_user_id=actor_id)

    assert recipients == [user]
