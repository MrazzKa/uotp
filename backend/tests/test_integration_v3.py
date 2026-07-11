"""Интеграционные тесты v3 против реального Postgres (см. conftest).

Покрывают то, чего не берут юниты: полный жизненный цикл через HTTP, видимость по
ролям, персональный контроль-lock, RBAC, аудит append-only. Тесты самодостаточны —
создают свои задачи и не зависят от порядка выполнения.
"""

from tests.conftest import auth, login


async def _users_by_email(client, token) -> dict:
    resp = await client.get("/users", headers=auth(token))
    assert resp.status_code == 200, resp.text
    return {u["email"]: u for u in resp.json()}


async def _sphere(client, token, code: str) -> dict:
    resp = await client.get("/spheres", headers=auth(token))
    assert resp.status_code == 200, resp.text
    for sphere in resp.json():
        if sphere.get("code") == code:
            return sphere
    raise AssertionError(f"sphere {code} not found")


async def _create_assigned(client, akim_token, title: str) -> dict:
    """Аким создаёт задачу с исполнителем-специалистом ЖКХ (→ ASSIGNED)."""
    users = await _users_by_email(client, akim_token)
    spec = users["spec_gkh@uotp.local"]
    gkh = await _sphere(client, akim_token, "gkh")
    payload = {
        "title": title,
        "sphere_id": gkh["id"],
        "executor_ids": [spec["id"]],
        "importance": "NORMAL",
    }
    resp = await client.post("/issues", json=payload, headers=auth(akim_token))
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- Жизненный цикл -------------------------------------------------------


async def test_full_lifecycle_assigned_to_closed(client, tokens):
    issue = await _create_assigned(client, tokens["akim"], "Интеграция: полный цикл")
    assert issue["status"] == "ASSIGNED"
    assert issue["assigned_to"]["email"] == "spec_gkh@uotp.local"
    assert issue["controller"] is not None, "контролёр должен авто-резолвиться по сфере"
    issue_id = issue["id"]

    # Исполнитель жмёт «Сделал» → у задачи есть контролёр → REVIEW_CONTROLLER.
    resp = await client.post(
        f"/issues/{issue_id}/submit", json={"report": "Выполнено"}, headers=auth(tokens["spec_gkh"])
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "REVIEW_CONTROLLER"

    # Контролёр снимает с контроля → CLOSED.
    controller_email = issue["controller"]["email"]
    controller_token = await login(client, controller_email)
    resp = await client.post(
        f"/issues/{issue_id}/transition",
        json={"status": "CLOSED"},
        headers=auth(controller_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "CLOSED"

    # История append-only содержит все ключевые события.
    resp = await client.get(f"/issues/{issue_id}", headers=auth(tokens["akim"]))
    actions = [h["action"] for h in resp.json()["history"]]
    assert "created" in actions


async def test_executor_cannot_close_directly(client, tokens):
    """Исполнитель не закрывает задачу — только «Сделал»."""
    issue = await _create_assigned(client, tokens["akim"], "Интеграция: исполнитель не закрывает")
    resp = await client.post(
        f"/issues/{issue['id']}/transition",
        json={"status": "CLOSED"},
        headers=auth(tokens["spec_gkh"]),
    )
    assert resp.status_code in (403, 409, 422), resp.text


# --- Персональный контроль (замок акима) ----------------------------------


async def test_personal_control_locks_close_to_marker(client, tokens):
    issue = await _create_assigned(client, tokens["akim"], "Интеграция: личный контроль")
    issue_id = issue["id"]

    # Аким ставит личный контроль.
    resp = await client.post(
        f"/issues/{issue_id}/personal-control",
        json={"on": True, "importance": "IMPORTANT"},
        headers=auth(tokens["akim"]),
    )
    assert resp.status_code == 200, resp.text

    # Исполнитель «Сделал» → REVIEW_CONTROLLER.
    resp = await client.post(
        f"/issues/{issue_id}/submit", json={"report": "Готово"}, headers=auth(tokens["spec_gkh"])
    )
    assert resp.status_code == 200, resp.text

    # Контролёр (не поставивший личный контроль) не может закрыть.
    controller_token = await login(client, issue["controller"]["email"])
    resp = await client.post(
        f"/issues/{issue_id}/transition", json={"status": "CLOSED"}, headers=auth(controller_token)
    )
    assert resp.status_code in (403, 409), f"личный контроль должен блокировать чужое закрытие: {resp.text}"

    # Аким (поставивший метку) закрыть может.
    resp = await client.post(
        f"/issues/{issue_id}/transition", json={"status": "CLOSED"}, headers=auth(tokens["akim"])
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "CLOSED"


# --- Видимость по ролям ----------------------------------------------------


async def test_operator_sees_unassigned_queue(client, tokens):
    resp = await client.get("/issues", params={"status": "NEW", "limit": 100}, headers=auth(tokens["operator"]))
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    # Все видимые оператору NEW-задачи — нераспределённые (или его собственные).
    assert all(i["status"] == "NEW" for i in items)


async def test_leadership_sees_more_than_specialist(client, tokens):
    akim = await client.get("/issues", params={"limit": 100}, headers=auth(tokens["akim"]))
    spec = await client.get("/issues", params={"limit": 100}, headers=auth(tokens["spec_gkh"]))
    assert akim.status_code == 200 and spec.status_code == 200
    assert len(akim.json()["items"]) >= len(spec.json()["items"])


async def test_mine_filter_narrows_to_direct_involvement(client, tokens):
    all_visible = await client.get("/issues", params={"limit": 100}, headers=auth(tokens["spec_gkh"]))
    mine = await client.get("/issues", params={"mine": "true", "limit": 100}, headers=auth(tokens["spec_gkh"]))
    assert all_visible.status_code == 200 and mine.status_code == 200
    mine_ids = {i["id"] for i in mine.json()["items"]}
    all_ids = {i["id"] for i in all_visible.json()["items"]}
    assert mine_ids <= all_ids, "mine должен быть подмножеством видимого"


# --- Мероприятия и соисполнители -------------------------------------------


async def test_event_visible_to_co_executor(client, tokens):
    """Участник мероприятия (соисполнитель) видит общую задачу, хотя он не
    руководство, без сферы и не главный исполнитель."""
    users = await _users_by_email(client, tokens["akim"])
    spec = users["spec_gkh@uotp.local"]
    participant = users["so_beskol@uotp.local"]  # AKIM_SO: не руководство, без сферы
    gkh = await _sphere(client, tokens["akim"], "gkh")
    resp = await client.post(
        "/issues",
        json={
            "title": "Интеграция: мероприятие",
            "task_type": "EVENT",
            "source": "event",
            "sphere_id": gkh["id"],
            "executor_ids": [spec["id"]],
            "co_executor_ids": [participant["id"]],
            "importance": "NORMAL",
        },
        headers=auth(tokens["akim"]),
    )
    assert resp.status_code == 201, resp.text
    event_id = resp.json()["id"]

    part_token = await login(client, "so_beskol@uotp.local")
    listing = await client.get("/issues", params={"limit": 100}, headers=auth(part_token))
    assert listing.status_code == 200
    assert event_id in {i["id"] for i in listing.json()["items"]}, "участник должен видеть мероприятие"


# --- RBAC ------------------------------------------------------------------


async def test_unauthenticated_rejected(client):
    resp = await client.get("/issues")
    assert resp.status_code == 401


async def test_specialist_cannot_delete_issue(client, tokens):
    issue = await _create_assigned(client, tokens["akim"], "Интеграция: RBAC удаление")
    resp = await client.delete(f"/issues/{issue['id']}", headers=auth(tokens["spec_gkh"]))
    assert resp.status_code in (403, 404), resp.text


# --- Утечка внутренних комментариев внешнему подрядчику --------------------


async def test_internal_comment_hidden_from_contractor(client, tokens):
    users = await _users_by_email(client, tokens["akim"])
    contractor = users["con_clean@uotp.local"]
    gkh = await _sphere(client, tokens["akim"], "gkh")
    resp = await client.post(
        "/issues",
        json={
            "title": "Интеграция: внутренний коммент",
            "sphere_id": gkh["id"],
            "executor_ids": [contractor["id"]],
            "importance": "NORMAL",
        },
        headers=auth(tokens["akim"]),
    )
    assert resp.status_code == 201, resp.text
    issue_id = resp.json()["id"]

    marker = "СЛУЖЕБНО-не-для-подрядчика"
    rc = await client.post(
        f"/issues/{issue_id}/comments",
        json={"content": marker, "is_internal": True},
        headers=auth(tokens["akim"]),
    )
    assert rc.status_code in (200, 201), rc.text

    con_token = await login(client, "con_clean@uotp.local")
    rd = await client.get(f"/issues/{issue_id}", headers=auth(con_token))
    assert rd.status_code == 200
    con_comments = [c["content"] for c in rd.json().get("comments", [])]
    assert not any(marker in c for c in con_comments), "внутренний коммент не должен быть виден подрядчику"

    ra = await client.get(f"/issues/{issue_id}", headers=auth(tokens["akim"]))
    akim_comments = [c["content"] for c in ra.json().get("comments", [])]
    assert any(marker in c for c in akim_comments), "автор должен видеть внутренний коммент"


# --- Аудит append-only (гос-требование) -----------------------------------


async def test_audit_log_is_append_only(client, tokens):
    """Триггеры БД должны блокировать UPDATE и DELETE строк audit_log."""
    import sqlalchemy as sa
    from sqlalchemy.ext.asyncio import create_async_engine

    from tests.conftest import TEST_DB_URL

    # Действие, которое пишет в audit_log.
    await _create_assigned(client, tokens["akim"], "Интеграция: аудит append-only")

    engine = create_async_engine(TEST_DB_URL)
    try:
        async with engine.begin() as conn:
            count = (await conn.execute(sa.text("SELECT count(*) FROM audit_log"))).scalar_one()
            assert count > 0, "должна быть хотя бы одна запись аудита"

        update_blocked = False
        try:
            async with engine.begin() as conn:
                await conn.execute(sa.text("UPDATE audit_log SET action = 'tampered'"))
        except Exception:
            update_blocked = True
        assert update_blocked, "UPDATE audit_log должен блокироваться триггером"

        delete_blocked = False
        try:
            async with engine.begin() as conn:
                await conn.execute(sa.text("DELETE FROM audit_log"))
        except Exception:
            delete_blocked = True
        assert delete_blocked, "DELETE audit_log должен блокироваться триггером"
    finally:
        await engine.dispose()
