from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class VoiceDraft(BaseModel):
    """Черновик задачи, собранный из голоса или текста.

    Пользователь проверяет и подтверждает его перед созданием задачи.
    Автоматического создания вслепую нет.
    """

    transcript: str
    title: str
    importance: str = "NORMAL"
    sphere_id: UUID | None = None
    sphere_name: str | None = None
    executor_id: UUID | None = None
    executor_name: str | None = None
    due_at: datetime | None = None
