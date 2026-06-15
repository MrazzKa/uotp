from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class DashboardCounts(BaseModel):
    in_progress: int
    overdue: int
    inspection: int
    closed_today: int
    new: int


class PerDayPoint(BaseModel):
    date: date
    count: int


class StatusPoint(BaseModel):
    status: str
    count: int


class HotZone(BaseModel):
    district_id: UUID | None
    name: str
    count: int


class RecentEvent(BaseModel):
    issue_id: UUID
    public_number: str
    action: str
    to_status: str | None
    created_at: datetime


class DashboardSummary(BaseModel):
    counts: DashboardCounts
    sla_on_time_pct: float
    per_day: list[PerDayPoint]
    by_status: list[StatusPoint]
    hot_zones: list[HotZone]
    recent_events: list[RecentEvent]
