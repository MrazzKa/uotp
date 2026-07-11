"""Интеграционная обвязка: реальный Postgres (uotp_test) + ASGI-клиент.

Стратегия:
- DATABASE_URL перенаправляется на отдельную тест-базу ДО импорта приложения,
  поэтому модульный engine (app.db) и seed работают с тест-базой.
- Схема пересоздаётся и миграции прогоняются один раз за сессию (нужны триггеры
  append-only audit_log), затем наполняется демо-сидом Бишкуля.
- Redis подменяется лёгким in-memory стабом (без внешних зависимостей), чтобы
  логин/logout/rate-limit/blacklist работали без живого Redis.
- Тесты, меняющие данные, создают свои задачи через API и не зависят от порядка.
"""

import os
import subprocess
import time
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://uotp:uotp@localhost:5432/uotp_test"
)

# Перенаправляем всё окружение на тест-базу и dev-режим ДО импорта приложения.
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["ENV"] = os.environ.get("ENV", "dev")
os.environ.pop("OPENAI_API_KEY", None)
# Лимитер логина бьёт напрямую в singleton-Redis мимо DI, поэтому в тестах
# (много логинов подряд) его отключаем поднятием порога, а не подменой Redis.
os.environ["LOGIN_RATE_LIMIT"] = "1000000"


class FakeRedis:
    """Минимальный async-стаб Redis (get/set/setex/incr/expire/delete/exists/ttl)."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get(self, key):
        return self._store.get(key)

    async def set(self, key, value, ex=None, *args, **kwargs):
        self._store[key] = str(value)
        return True

    async def setex(self, key, ttl, value):
        self._store[key] = str(value)
        return True

    async def delete(self, *keys):
        removed = 0
        for key in keys:
            if key in self._store:
                del self._store[key]
                removed += 1
        return removed

    async def exists(self, key):
        return 1 if key in self._store else 0

    async def incr(self, key):
        value = int(self._store.get(key, "0")) + 1
        self._store[key] = str(value)
        return value

    async def expire(self, key, ttl):
        return True

    async def ttl(self, key):
        return -1

    async def flushdb(self):
        self._store.clear()


async def _reset_schema() -> None:
    """Пересоздать схему public напрямую через подключение (без docker exec).

    Работает и локально, и в CI. Расширения (postgis/vector/pg_trgm) пересоздаются
    миграцией 0001 после сброса.
    """
    import sqlalchemy as sa
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(TEST_DB_URL, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as conn:
            await conn.execute(sa.text("DROP SCHEMA IF EXISTS public CASCADE"))
            await conn.execute(sa.text("CREATE SCHEMA public"))
    finally:
        await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _prepare_database():
    """Пересоздать схему тест-базы и прогнать миграции + seed один раз за сессию."""
    import asyncio

    env = {**os.environ, "DATABASE_URL": TEST_DB_URL, "ENV": "dev"}
    try:
        asyncio.run(_reset_schema())
    except Exception as exc:  # БД недоступна — пропускаем интеграционный слой
        pytest.skip(f"Тест-база недоступна: {exc}")

    migrate = subprocess.run(
        ["python", "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    assert migrate.returncode == 0, f"alembic upgrade failed:\n{migrate.stderr}"

    seed = subprocess.run(
        ["python", "-m", "app.seed"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    assert seed.returncode == 0, f"seed failed:\n{seed.stderr}\n{seed.stdout}"
    yield


@pytest.fixture()
async def client():
    """ASGI-клиент с подменённым Redis; lifespan не запускается (без планировщика)."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app
    from app.redis import get_redis

    fake = FakeRedis()

    async def _get_redis_override():
        yield fake

    app.dependency_overrides[get_redis] = _get_redis_override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as ac:
        yield ac
    app.dependency_overrides.pop(get_redis, None)


async def login(client, email: str, password: str = "demo123") -> str:
    """Вернуть access-токен для пользователя демо-сида."""
    resp = await client.post("/auth/login", json={"login": email, "password": password})
    assert resp.status_code == 200, f"login {email} failed: {resp.status_code} {resp.text}"
    return resp.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# Демо-пользователи Бишкульского сида (email → роль).
DEMO_USERS = {
    "admin": "admin@uotp.local",
    "akim": "akim@uotp.local",
    "operator": "operator@uotp.local",
    "spec_gkh": "spec_gkh@uotp.local",
    "spec_road": "spec_road@uotp.local",
    "spec_edu": "spec_edu@uotp.local",
}


@pytest.fixture()
async def tokens(client):
    """Словарь роль→токен для основных демо-пользователей."""
    out = {}
    for key, email in DEMO_USERS.items():
        try:
            out[key] = await login(client, email)
        except AssertionError:
            pass
    return out
