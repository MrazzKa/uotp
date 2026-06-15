from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.modules.notifications.schemas import (
    DeviceRegister,
    DeviceUnregister,
    NotificationListResponse,
    NotificationRead,
    UnreadCountResponse,
)
from app.modules.notifications.service import (
    list_notifications,
    mark_all_read,
    mark_read,
    register_device,
    unregister_device,
    unread_count,
)
from app.modules.users.models import User

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=NotificationListResponse)
async def notifications_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    is_read: bool | None = None,
    cursor: str | None = None,
    limit: int = Query(default=30, ge=1, le=100),
):
    items, next_cursor = await list_notifications(
        session, current_user, is_read=is_read, cursor=cursor, limit=limit
    )
    return {"items": items, "next_cursor": next_cursor}


@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
async def unread_count_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return {"count": await unread_count(session, current_user)}


@router.post("/notifications/{notification_id}/read", response_model=NotificationRead)
async def mark_read_endpoint(
    notification_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    notification = await mark_read(session, current_user, notification_id)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return notification


@router.post("/notifications/read-all", response_model=UnreadCountResponse)
async def read_all_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return {"count": await mark_all_read(session, current_user)}


@router.post("/devices/register", status_code=status.HTTP_204_NO_CONTENT)
async def register_device_endpoint(
    payload: DeviceRegister,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    await register_device(session, current_user, payload.expo_push_token, payload.platform)


@router.post("/devices/unregister", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_device_endpoint(
    payload: DeviceUnregister,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    await unregister_device(session, current_user, payload.expo_push_token)
