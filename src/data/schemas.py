"""
Pydantic Data Contracts and Validation Schemas for GeoPulse.
Enforces strict type safety, coordinate constraints, and business logic
across the retail mobility data pipeline.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class POISchema(BaseModel):
    """Schema representing a retail Point of Interest (POI)."""

    id: str = Field(..., description="Unique POI identifier (e.g. OSM node ID)")
    name: str = Field(..., min_length=1, description="Business or venue name")
    category: str = Field(..., description="Retail category (e.g. cafe, apparel, supermarket)")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 Latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 Longitude")
    city: str = Field(..., description="City name (e.g. Bengaluru, Pune)")
    rating: Optional[float] = Field(None, ge=1.0, le=5.0, description="Customer rating out of 5.0")
    brand: Optional[str] = Field(None, description="Retail brand chain if applicable")

    @field_validator("name")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Name cannot be empty or purely whitespace")
        return cleaned


class FootfallPingSchema(BaseModel):
    """Schema representing a single aggregated or anonymized mobility telemetry ping."""

    ping_id: str = Field(..., description="Unique telemetry ping ID")
    device_id: str = Field(..., description="Anonymized device/hash identifier")
    timestamp: datetime = Field(..., description="Timestamp of the footfall event")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 Latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 Longitude")
    dwell_time_minutes: float = Field(..., ge=0.0, le=1440.0, description="Dwell duration in minutes")
    zone_id: Optional[str] = Field(None, description="Spatial cluster or hex cell identifier")
    is_weekend: bool = Field(..., description="Whether the event occurred on Saturday/Sunday")


class StoreMetricSchema(BaseModel):
    """Schema representing analytical aggregated performance metrics for a retail store."""

    store_id: str = Field(..., description="Unique store ID")
    store_name: str = Field(..., description="Store or branch name")
    category: str = Field(..., description="Retail category")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    daily_footfall: int = Field(..., ge=0, description="Average daily footfall count")
    avg_dwell_minutes: float = Field(..., ge=0.0, description="Average customer dwell duration")
    passerby_count: int = Field(..., ge=0, description="Count of quick pedestrian passersby (< 5 min)")
    shopper_count: int = Field(..., ge=0, description="Count of high-intent engaged shoppers (> 15 min)")
    conversion_rate: float = Field(..., ge=0.0, le=1.0, description="Shopper conversion ratio (0.0 to 1.0)")
