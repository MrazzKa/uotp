from typing import Any, Literal

from pydantic import BaseModel, Field


class GeoJSONFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: str | None = None
    geometry: dict[str, Any] | None
    properties: dict[str, Any] = Field(default_factory=dict)


class GeoJSONFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[GeoJSONFeature]
    truncated: bool = False


class ClusterPoint(BaseModel):
    longitude: float
    latitude: float
    count: int
    dominant_status: str


class HeatmapPoint(BaseModel):
    longitude: float
    latitude: float
    weight: int
