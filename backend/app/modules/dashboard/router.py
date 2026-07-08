from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.modules.dashboard.schemas import DashboardSummary, OkrugDetail
from app.modules.dashboard.service import dashboard_summary, okrug_detail
from app.modules.users.models import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def summary_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return await dashboard_summary(session, current_user)


@router.get("/okrug/{department_id}", response_model=OkrugDetail)
async def okrug_detail_endpoint(
    department_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    detail = await okrug_detail(session, current_user, department_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Округ не найден.")
    return detail
