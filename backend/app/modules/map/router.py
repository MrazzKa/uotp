from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.modules.map.schemas import ClusterPoint, GeoJSONFeatureCollection, HeatmapPoint
from app.modules.map.service import clusters, district_features, heatmap_points, issue_features, parse_bbox
from app.modules.users.models import User

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/issues", response_model=GeoJSONFeatureCollection)
async def map_issues(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    bbox: str = Query(..., description="minLon,minLat,maxLon,maxLat"),
    status_value: Annotated[str | None, Query(alias="status")] = None,
    category: UUID | None = None,
    district: UUID | None = None,
    priority: str | None = None,
    assigned_to: UUID | None = None,
    is_overdue: bool | None = None,
):
    return await issue_features(
        session,
        current_user,
        bbox=parse_bbox(bbox),
        status_value=status_value,
        category=category,
        district=district,
        priority=priority,
        assigned_to=assigned_to,
        is_overdue=is_overdue,
    )


@router.get("/clusters", response_model=list[ClusterPoint])
async def map_clusters(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    bbox: str = Query(..., description="minLon,minLat,maxLon,maxLat"),
    zoom: int = Query(..., ge=1, le=22),
    status_value: Annotated[str | None, Query(alias="status")] = None,
    category: UUID | None = None,
    district: UUID | None = None,
    priority: str | None = None,
    assigned_to: UUID | None = None,
    is_overdue: bool | None = None,
):
    return await clusters(
        session,
        current_user,
        bbox=parse_bbox(bbox),
        zoom=zoom,
        status_value=status_value,
        category=category,
        district=district,
        priority=priority,
        assigned_to=assigned_to,
        is_overdue=is_overdue,
    )


@router.get("/heatmap", response_model=list[HeatmapPoint])
async def map_heatmap(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    bbox: str = Query(..., description="minLon,minLat,maxLon,maxLat"),
    status_value: Annotated[str | None, Query(alias="status")] = None,
    category: UUID | None = None,
    district: UUID | None = None,
    priority: str | None = None,
    assigned_to: UUID | None = None,
    is_overdue: bool | None = None,
):
    return await heatmap_points(
        session,
        current_user,
        bbox=parse_bbox(bbox),
        status_value=status_value,
        category=category,
        district=district,
        priority=priority,
        assigned_to=assigned_to,
        is_overdue=is_overdue,
    )


@router.get("/districts", response_model=GeoJSONFeatureCollection)
async def map_districts(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return await district_features(session, current_user)
