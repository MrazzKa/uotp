import json
from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import District
from app.modules.issues.models import Issue, IssueAssignee
from app.modules.users.models import User

PETROPAVLOVSK_BBOX = (69.05, 54.80, 69.25, 54.93)


@dataclass(frozen=True)
class BBox:
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    @property
    def envelope(self):
        return func.ST_MakeEnvelope(self.min_lon, self.min_lat, self.max_lon, self.max_lat, 4326)


def parse_bbox(value: str) -> BBox:
    try:
        parts = [float(part.strip()) for part in value.split(",")]
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid bbox") from exc
    if len(parts) != 4:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid bbox")
    min_lon, min_lat, max_lon, max_lat = parts
    if min_lon >= max_lon or min_lat >= max_lat:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid bbox")
    return BBox(min_lon, min_lat, max_lon, max_lat)


def role_filtered_statement(user: User) -> Select:
    statement = select(Issue).where(
        Issue.tenant_id == user.tenant_id,
        Issue.deleted_at.is_(None),
        Issue.geometry.is_not(None),
    )
    if user.role.code == "EXECUTOR":
        statement = statement.outerjoin(IssueAssignee, IssueAssignee.issue_id == Issue.id).where(
            or_(Issue.assigned_to_id == user.id, IssueAssignee.user_id == user.id)
        )
    return statement


def apply_filters(
    statement: Select,
    *,
    bbox: BBox,
    status_value: str | None = None,
    category: UUID | None = None,
    district: UUID | None = None,
    priority: str | None = None,
    assigned_to: UUID | None = None,
    is_overdue: bool | None = None,
) -> Select:
    filters = [func.ST_Intersects(Issue.geometry, bbox.envelope)]
    if status_value:
        filters.append(Issue.status == status_value)
    if category:
        filters.append(Issue.primary_category_id == category)
    if district:
        filters.append(Issue.district_id == district)
    if priority:
        filters.append(Issue.priority == priority)
    if assigned_to:
        filters.append(Issue.assigned_to_id == assigned_to)
    if is_overdue is not None:
        filters.append(Issue.is_overdue.is_(is_overdue))
    return statement.where(and_(*filters))


async def issue_features(
    session: AsyncSession,
    user: User,
    *,
    bbox: BBox,
    status_value: str | None = None,
    category: UUID | None = None,
    district: UUID | None = None,
    priority: str | None = None,
    assigned_to: UUID | None = None,
    is_overdue: bool | None = None,
    limit: int = 2000,
) -> dict:
    statement = apply_filters(
        role_filtered_statement(user),
        bbox=bbox,
        status_value=status_value,
        category=category,
        district=district,
        priority=priority,
        assigned_to=assigned_to,
        is_overdue=is_overdue,
    ).add_columns(func.ST_AsGeoJSON(Issue.geometry).label("geojson")).limit(limit + 1)
    result = await session.execute(statement)
    rows = result.unique().all()
    truncated = len(rows) > limit
    features = []
    for issue, geojson in rows[:limit]:
        geometry = json.loads(geojson)
        features.append(
            {
                "type": "Feature",
                "id": str(issue.id),
                "geometry": geometry,
                "properties": {
                    "id": str(issue.id),
                    "public_number": issue.public_number,
                    "status": issue.status,
                    "priority": issue.priority,
                    "category": issue.category.name_ru if issue.category else None,
                    "address": issue.address,
                    "title": issue.title,
                    "is_overdue": issue.is_overdue,
                    "sla_due_at": issue.sla_due_at.isoformat() if issue.sla_due_at else None,
                },
            }
        )
    return {"type": "FeatureCollection", "features": features, "truncated": truncated}


def grid_size_for_zoom(zoom: int) -> float:
    zoom = max(1, min(18, zoom))
    return max(0.001, 0.08 / (2 ** max(0, zoom - 8)))


async def clusters(
    session: AsyncSession,
    user: User,
    *,
    bbox: BBox,
    zoom: int,
    status_value: str | None = None,
    category: UUID | None = None,
    district: UUID | None = None,
    priority: str | None = None,
    assigned_to: UUID | None = None,
    is_overdue: bool | None = None,
) -> list[dict]:
    grid = grid_size_for_zoom(zoom)
    statement = apply_filters(
        role_filtered_statement(user),
        bbox=bbox,
        status_value=status_value,
        category=category,
        district=district,
        priority=priority,
        assigned_to=assigned_to,
        is_overdue=is_overdue,
    ).subquery()
    snapped = func.ST_SnapToGrid(statement.c.geometry, grid)
    query = (
        select(
            func.ST_X(func.ST_Centroid(func.ST_Collect(statement.c.geometry))).label("longitude"),
            func.ST_Y(func.ST_Centroid(func.ST_Collect(statement.c.geometry))).label("latitude"),
            func.count().label("count"),
            func.mode().within_group(statement.c.status).label("dominant_status"),
        )
        .select_from(statement)
        .group_by(snapped)
        .order_by(func.count().desc())
        .limit(1000)
    )
    rows = (await session.execute(query)).mappings().all()
    return [
        {
            "longitude": float(row["longitude"]),
            "latitude": float(row["latitude"]),
            "count": int(row["count"]),
            "dominant_status": row["dominant_status"],
        }
        for row in rows
    ]


async def heatmap_points(
    session: AsyncSession,
    user: User,
    *,
    bbox: BBox,
    status_value: str | None = None,
    category: UUID | None = None,
    district: UUID | None = None,
    priority: str | None = None,
    assigned_to: UUID | None = None,
    is_overdue: bool | None = None,
) -> list[dict]:
    lon_span = bbox.max_lon - bbox.min_lon
    grid = max(0.002, lon_span / 45)
    statement = apply_filters(
        role_filtered_statement(user),
        bbox=bbox,
        status_value=status_value,
        category=category,
        district=district,
        priority=priority,
        assigned_to=assigned_to,
        is_overdue=is_overdue,
    ).subquery()
    snapped = func.ST_SnapToGrid(statement.c.geometry, grid)
    query = (
        select(
            func.ST_X(func.ST_Centroid(func.ST_Collect(statement.c.geometry))).label("longitude"),
            func.ST_Y(func.ST_Centroid(func.ST_Collect(statement.c.geometry))).label("latitude"),
            func.count().label("weight"),
        )
        .select_from(statement)
        .group_by(snapped)
        .limit(1500)
    )
    rows = (await session.execute(query)).mappings().all()
    return [
        {"longitude": float(row["longitude"]), "latitude": float(row["latitude"]), "weight": int(row["weight"])}
        for row in rows
    ]


async def district_features(session: AsyncSession, user: User) -> dict:
    query = (
        select(
            District.id,
            District.name_ru,
            District.name_kk,
            District.code,
            func.ST_AsGeoJSON(District.geometry).label("geometry"),
        )
        .where(District.tenant_id == user.tenant_id, District.deleted_at.is_(None), District.geometry.is_not(None))
        .order_by(District.name_ru)
    )
    rows = (await session.execute(query)).mappings().all()
    features = [
        {
            "type": "Feature",
            "id": str(row["id"]),
            "geometry": json.loads(row["geometry"]),
            "properties": {
                "id": str(row["id"]),
                "name_ru": row["name_ru"],
                "name_kk": row["name_kk"],
                "code": row["code"],
            },
        }
        for row in rows
    ]
    return {"type": "FeatureCollection", "features": features, "truncated": False}
