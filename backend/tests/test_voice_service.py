from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.voice.service import (
    build_draft,
    match_sphere,
    match_user,
    normalize_importance,
    parse_due,
)

NOW = datetime(2026, 7, 6, 9, 0, tzinfo=UTC)


def _sphere(sid, name):
    return SimpleNamespace(id=sid, name_ru=name)


def _user(uid, name):
    return SimpleNamespace(id=uid, full_name=name)


SPHERES = [_sphere("s1", "ЖКХ, транспорт и дороги"), _sphere("s2", "Образование")]
USERS = [_user("u1", "Асхат Нурланов"), _user("u2", "Марина Ли")]


def test_normalize_importance() -> None:
    assert normalize_importance("срочно") == "URGENT"
    assert normalize_importance("важно") == "IMPORTANT"
    assert normalize_importance("") == "NORMAL"
    assert normalize_importance(None) == "NORMAL"
    assert normalize_importance("что-то") == "NORMAL"


def test_parse_due_relative() -> None:
    assert parse_due("завтра", NOW).date() == datetime(2026, 7, 7, tzinfo=UTC).date()
    assert parse_due("сегодня", NOW).date() == datetime(2026, 7, 6, tzinfo=UTC).date()
    assert parse_due("послезавтра", NOW).date() == datetime(2026, 7, 8, tzinfo=UTC).date()
    assert parse_due("через 3 дня", NOW).date() == datetime(2026, 7, 9, tzinfo=UTC).date()
    assert parse_due("через неделю", NOW).date() == datetime(2026, 7, 13, tzinfo=UTC).date()
    assert parse_due("", NOW) is None
    assert parse_due(None, NOW) is None


def test_match_sphere() -> None:
    assert match_sphere("жкх", SPHERES).id == "s1"
    assert match_sphere("образование", SPHERES).id == "s2"
    assert match_sphere("дороги", SPHERES).id == "s1"
    assert match_sphere("ветеринария", SPHERES) is None
    assert match_sphere(None, SPHERES) is None


def test_match_user() -> None:
    assert match_user("Нурланов", USERS).id == "u1"
    assert match_user("Асхат Нурланов", USERS).id == "u1"
    assert match_user("Марина", USERS).id == "u2"
    assert match_user("Иванов", USERS) is None
    assert match_user(None, USERS) is None


def test_build_draft_maps_fields() -> None:
    parsed = {"title": "Заменить фонари на центральной улице", "importance": "срочно", "sphere": "жкх", "executor": "Нурланов", "due": "завтра"}
    draft = build_draft("сырой текст", parsed, SPHERES, USERS, now=NOW)
    assert draft["title"] == "Заменить фонари на центральной улице"
    assert draft["importance"] == "URGENT"
    assert draft["sphere_id"] == "s1"
    assert draft["executor_id"] == "u1"
    assert draft["due_at"].date() == datetime(2026, 7, 7, tzinfo=UTC).date()
    assert draft["transcript"] == "сырой текст"


def test_build_draft_falls_back_to_transcript() -> None:
    draft = build_draft("почини дорогу", {}, SPHERES, USERS, now=NOW)
    assert draft["title"] == "почини дорогу"
    assert draft["importance"] == "NORMAL"
    assert draft["sphere_id"] is None
    assert draft["executor_id"] is None
    assert draft["due_at"] is None
