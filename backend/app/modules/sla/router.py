from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_roles
from app.modules.sla.models import SlaRule
from app.modules.sla.schemas import SlaRuleRead, SlaRuleUpsert
from app.modules.users.models import User

router = APIRouter(prefix="/admin/rules/sla", tags=["admin-sla"])


@router.get("", response_model=list[SlaRuleRead])
async def list_sla_rules(
    current_user: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(
        select(SlaRule)
        .where(SlaRule.tenant_id == current_user.tenant_id, SlaRule.deleted_at.is_(None))
        .order_by(SlaRule.category_id.nulls_last(), SlaRule.priority.nulls_last())
    )
    return result.scalars().all()


@router.post("", response_model=SlaRuleRead)
async def upsert_sla_rule(
    payload: SlaRuleUpsert,
    current_user: Annotated[User, Depends(require_roles("ADMIN"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    category_filter = (
        SlaRule.category_id == payload.category_id
        if payload.category_id
        else SlaRule.category_id.is_(None)
    )
    priority_filter = SlaRule.priority == payload.priority if payload.priority else SlaRule.priority.is_(None)
    rule = (
        await session.execute(
            select(SlaRule).where(
                SlaRule.tenant_id == current_user.tenant_id,
                SlaRule.deleted_at.is_(None),
                category_filter,
                priority_filter,
            )
        )
    ).scalar_one_or_none()
    data = payload.model_dump()
    if rule is None:
        rule = SlaRule(tenant_id=current_user.tenant_id, **data)
        session.add(rule)
    else:
        for key, value in data.items():
            setattr(rule, key, value)
    await session.commit()
    await session.refresh(rule)
    return rule
