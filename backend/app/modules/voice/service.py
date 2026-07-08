"""Голосовой модуль: распознавание речи и разбор задачи.

Провайдер сменный. Сейчас реализован OpenAI (распознавание Whisper и разбор GPT).
Разбор устроен так: OpenAI возвращает поля в свободной форме, а сопоставление со
справочниками (сфера, исполнитель), нормализация важности и вычисление срока делаются
локально чистыми функциями (их и покрываем тестами, без обращения к сети).
"""
import json
import re
from datetime import datetime, time, timedelta

import httpx

from app.config import settings

IMPORTANCE_URGENT = {"urgent", "срочно", "срочная", "срочное", "критично", "критическая", "high", "критичная"}
IMPORTANCE_IMPORTANT = {"important", "важно", "важная", "важное", "medium", "приоритетно"}


def voice_configured() -> bool:
    return bool(settings.openai_api_key)


def normalize_importance(value: str | None) -> str:
    token = (value or "").strip().lower()
    if token in IMPORTANCE_URGENT:
        return "URGENT"
    if token in IMPORTANCE_IMPORTANT:
        return "IMPORTANT"
    return "NORMAL"


def parse_due(hint: str | None, now: datetime) -> datetime | None:
    """Простой разбор относительного срока из подсказки.

    Понимает: сегодня, завтра, послезавтра, через N дней, N дней, на неделе/через неделю.
    Дефолтное время исполнения к концу рабочего дня (18:00).
    """
    text = (hint or "").strip().lower()
    if not text:
        return None
    end_of_day = time(hour=18, minute=0)

    def at(day_offset: int) -> datetime:
        return datetime.combine((now + timedelta(days=day_offset)).date(), end_of_day, tzinfo=now.tzinfo)

    if "послезавтра" in text:
        return at(2)
    if "завтра" in text:
        return at(1)
    if "сегодня" in text:
        return at(0)
    week = re.search(r"(через\s+недел|на\s+недел)", text)
    if week:
        return at(7)
    days = re.search(r"(\d+)\s*(?:раб\w*\s*)?(?:дн|день|дня|дней)", text)
    if days:
        return at(int(days.group(1)))
    return None


def _tokens(value: str) -> set[str]:
    return {token for token in re.split(r"[\s,.]+", value.lower()) if len(token) > 2}


def match_sphere(name: str | None, spheres: list):
    if not name:
        return None
    needle = name.strip().lower()
    for sphere in spheres:
        haystack = sphere.name_ru.lower()
        if needle and (needle in haystack or haystack in needle):
            return sphere
    needle_tokens = _tokens(name)
    for sphere in spheres:
        if needle_tokens & _tokens(sphere.name_ru):
            return sphere
    return None


def match_user(name: str | None, users: list):
    if not name:
        return None
    needle = name.strip().lower()
    for user in users:
        haystack = user.full_name.lower()
        if needle in haystack or haystack in needle:
            return user
    needle_tokens = _tokens(name)
    for user in users:
        if needle_tokens & _tokens(user.full_name):
            return user
    return None


def build_draft(transcript: str, parsed: dict, spheres: list, users: list, now: datetime | None = None) -> dict:
    """Собрать черновик из распознанного текста и полей от модели (чистая функция)."""
    now = now or datetime.now()
    sphere = match_sphere(parsed.get("sphere"), spheres)
    executor = match_user(parsed.get("executor"), users)
    title = (parsed.get("title") or transcript or "").strip()
    return {
        "transcript": transcript,
        "title": title,
        "importance": normalize_importance(parsed.get("importance")),
        "sphere_id": sphere.id if sphere else None,
        "sphere_name": sphere.name_ru if sphere else parsed.get("sphere"),
        "executor_id": executor.id if executor else None,
        "executor_name": executor.full_name if executor else parsed.get("executor"),
        "due_at": parse_due(parsed.get("due"), now),
    }


async def transcribe_audio(content: bytes, filename: str) -> str:
    """Распознать речь через OpenAI (Whisper)."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.openai_base_url}/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            files={"file": (filename, content)},
            data={"model": settings.openai_stt_model},
        )
    response.raise_for_status()
    return response.json().get("text", "").strip()


PARSE_SYSTEM_PROMPT = (
    "Ты помощник акима района. Из текста устной задачи выдели поля и верни строго JSON без пояснений. "
    "Поля: title (краткая формулировка задачи), importance (одно из: срочно, важно, обычная), "
    "sphere (сфера или отдел, если упомянута), executor (ФИО или должность исполнителя, если названы), "
    "due (срок словами как в тексте, например завтра, через 3 дня). "
    "Если поля нет, ставь пустую строку. Отвечай на русском."
)


async def parse_task_text(transcript: str, spheres: list, users: list) -> dict:
    """Разобрать текст задачи через OpenAI (GPT). Возвращает словарь полей в свободной форме."""
    sphere_hint = ", ".join(sphere.name_ru for sphere in spheres[:20])
    user_hint = ", ".join(user.full_name for user in users[:40])
    user_prompt = (
        f"Текст задачи: {transcript}\n"
        f"Возможные сферы: {sphere_hint}\n"
        f"Возможные исполнители: {user_hint}"
    )
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.openai_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_parse_model,
                "messages": [
                    {"role": "system", "content": PARSE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0,
            },
        )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return {"title": transcript}
