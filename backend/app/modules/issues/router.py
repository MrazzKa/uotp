from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user, require_roles
from app.modules.audit.service import log_audit
from app.modules.issues.models import ExifData, Issue, IssueAttachment, IssueHistory
from app.modules.issues.schemas import (
    IssueAssign,
    IssueAttachmentRead,
    IssueCommentCreate,
    IssueCommentRead,
    IssueCreate,
    IssueDetail,
    IssueHistoryRead,
    IssueListResponse,
    IssuePersonalControl,
    IssueSubmit,
    IssueTransition,
    IssueUpdate,
)
from app.modules.issues.service import (
    add_attachments,
    add_comment,
    assign_issue,
    create_issue,
    get_issue_or_404,
    list_issues,
    set_personal_control,
    soft_delete_issue,
    submit_issue,
    transition_issue,
    update_issue,
)
from app.modules.issues.storage import presigned_url
from app.modules.users.models import User

router = APIRouter(prefix="/issues", tags=["issues"])


def _serialize_attachment(attachment) -> IssueAttachmentRead:
    read = IssueAttachmentRead.model_validate(attachment)
    read.file_url = presigned_url(read.file_url)
    read.medium_url = presigned_url(read.medium_url)
    read.thumbnail_url = presigned_url(read.thumbnail_url)
    return read


def serialize_issue_detail(issue: Issue, user: User) -> IssueDetail:
    detail = IssueDetail.model_validate(issue)
    detail.attachments = [_serialize_attachment(item) for item in issue.attachments]
    detail.on_personal_control = any(mark.user_id == user.id for mark in issue.personal_marks)
    # Специалистам-исполнителям не показываем служебные (internal) комментарии.
    if user.role is not None and user.role.code == "SPECIALIST":
        detail.comments = [c for c in detail.comments if not c.is_internal]
    return detail


@router.post("", response_model=IssueDetail, status_code=status.HTTP_201_CREATED)
async def create_issue_endpoint(
    payload: IssueCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    issue = await create_issue(session, payload, current_user)
    return serialize_issue_detail(issue, current_user)


@router.get("", response_model=IssueListResponse)
async def list_issues_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    status_value: Annotated[str | None, Query(alias="status")] = None,
    category: UUID | None = None,
    district: UUID | None = None,
    assigned_to: UUID | None = None,
    sphere: UUID | None = None,
    importance: str | None = None,
    priority: str | None = None,
    source: str | None = None,
    is_overdue: bool | None = None,
    personal: bool | None = None,
    q: str | None = None,
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
):
    items, next_cursor = await list_issues(
        session,
        current_user,
        status_value=status_value,
        category_id=category,
        district_id=district,
        assigned_to_id=assigned_to,
        sphere_id=sphere,
        importance=importance,
        priority=priority,
        source=source,
        is_overdue=is_overdue,
        personal=personal,
        q=q,
        cursor=cursor,
        limit=limit,
    )
    return {"items": items, "next_cursor": next_cursor}


@router.get("/{issue_id}", response_model=IssueDetail)
async def get_issue_endpoint(
    issue_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    issue = await get_issue_or_404(session, issue_id, current_user)
    return serialize_issue_detail(issue, current_user)


@router.patch("/{issue_id}", response_model=IssueDetail)
async def update_issue_endpoint(
    issue_id: UUID,
    payload: IssueUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    issue = await get_issue_or_404(session, issue_id, current_user)
    updated = await update_issue(session, issue, payload, current_user)
    return serialize_issue_detail(updated, current_user)


@router.delete("/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_issue_endpoint(
    issue_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    issue = await get_issue_or_404(session, issue_id, current_user)
    await soft_delete_issue(session, issue, current_user)


@router.post("/{issue_id}/assign", response_model=IssueDetail)
async def assign_issue_endpoint(
    issue_id: UUID,
    payload: IssueAssign,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    issue = await get_issue_or_404(session, issue_id, current_user)
    updated = await assign_issue(session, issue, payload, current_user)
    return serialize_issue_detail(updated, current_user)


@router.post("/{issue_id}/submit", response_model=IssueDetail)
async def submit_issue_endpoint(
    issue_id: UUID,
    payload: IssueSubmit,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    issue = await get_issue_or_404(session, issue_id, current_user)
    updated = await submit_issue(session, issue, current_user, payload.report)
    return serialize_issue_detail(updated, current_user)


@router.post("/{issue_id}/transition", response_model=IssueDetail)
async def transition_issue_endpoint(
    issue_id: UUID,
    payload: IssueTransition,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    issue = await get_issue_or_404(session, issue_id, current_user)
    updated = await transition_issue(session, issue, payload, current_user)
    return serialize_issue_detail(updated, current_user)


@router.post("/{issue_id}/personal-control", response_model=IssueDetail)
async def personal_control_endpoint(
    issue_id: UUID,
    payload: IssuePersonalControl,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    issue = await get_issue_or_404(session, issue_id, current_user)
    updated = await set_personal_control(session, issue, current_user, payload)
    return serialize_issue_detail(updated, current_user)


@router.post("/{issue_id}/attachments", response_model=list[IssueAttachmentRead])
async def upload_attachments_endpoint(
    issue_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    files: Annotated[list[UploadFile], File()],
    attachment_type: Annotated[str, Form()] = "before",
    latitude: Annotated[Decimal | None, Form()] = None,
    longitude: Annotated[Decimal | None, Form()] = None,
    taken_at: Annotated[datetime | None, Form()] = None,
):
    issue = await get_issue_or_404(session, issue_id, current_user)
    created = await add_attachments(
        session, issue, current_user, files, attachment_type, latitude, longitude, taken_at
    )
    return [_serialize_attachment(item) for item in created]


@router.post("/{issue_id}/comments", response_model=IssueCommentRead, status_code=status.HTTP_201_CREATED)
async def add_comment_endpoint(
    issue_id: UUID,
    payload: IssueCommentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    issue = await get_issue_or_404(session, issue_id, current_user)
    return await add_comment(
        session, issue, current_user, payload.content, payload.language, payload.is_internal
    )


@router.get("/{issue_id}/history", response_model=list[IssueHistoryRead])
async def history_endpoint(
    issue_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    issue = await get_issue_or_404(session, issue_id, current_user)
    result = await session.execute(
        select(IssueHistory).where(IssueHistory.issue_id == issue.id).order_by(IssueHistory.created_at)
    )
    return result.scalars().all()


@router.get("/{issue_id}/attachments/{attachment_id}/exif")
async def attachment_exif_endpoint(
    issue_id: UUID,
    attachment_id: UUID,
    current_user: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """ADMIN-only access to raw EXIF (personal data); every access is audited."""
    result = await session.execute(
        select(ExifData)
        .join(IssueAttachment, IssueAttachment.id == ExifData.attachment_id)
        .where(
            ExifData.attachment_id == attachment_id,
            ExifData.tenant_id == current_user.tenant_id,
            IssueAttachment.issue_id == issue_id,
        )
    )
    exif = result.scalar_one_or_none()
    if exif is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EXIF not found")
    await log_audit(
        session, current_user, "exif.access", "attachment", entity_id=attachment_id,
        context={"issue_id": str(issue_id)},
    )
    await session.commit()
    return {"attachment_id": str(attachment_id), "raw_exif": exif.raw_exif}
