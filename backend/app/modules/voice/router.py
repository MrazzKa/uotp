from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.modules.catalog.models import Sphere
from app.modules.users.models import User
from app.modules.voice.schemas import VoiceDraft
from app.modules.voice.service import (
    build_draft,
    parse_task_text,
    transcribe_audio,
    voice_configured,
)

router = APIRouter(prefix="/voice", tags=["voice"])


@router.get("/status")
async def voice_status(current_user: Annotated[User, Depends(get_current_user)]):
    return {"enabled": voice_configured()}


@router.post("/parse", response_model=VoiceDraft)
async def parse_voice(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    file: Annotated[UploadFile | None, File()] = None,
    text: Annotated[str | None, Form()] = None,
):
    """Голос или текст → черновик задачи (пользователь подтверждает вручную)."""
    if not voice_configured():
        raise HTTPException(status_code=503, detail="Голосовой модуль не настроен: не задан OPENAI_API_KEY.")

    if file is not None:
        content = await file.read()
        try:
            transcript = await transcribe_audio(content, file.filename or "audio.m4a")
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="Ошибка распознавания речи.") from exc
    elif text:
        transcript = text.strip()
    else:
        raise HTTPException(status_code=400, detail="Передайте аудио (file) или текст (text).")

    if not transcript:
        raise HTTPException(status_code=422, detail="Не удалось распознать текст.")

    spheres = (
        await session.execute(
            select(Sphere).where(Sphere.tenant_id == current_user.tenant_id, Sphere.deleted_at.is_(None))
        )
    ).scalars().all()
    users = (
        await session.execute(select(User).where(User.tenant_id == current_user.tenant_id))
    ).scalars().all()

    try:
        parsed = await parse_task_text(transcript, list(spheres), list(users))
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Ошибка разбора задачи.") from exc

    return build_draft(transcript, parsed, list(spheres), list(users))
