"""
Unit tests for GeoPulse Pydantic Data Schemas and Configuration loader.
"""

from datetime import datetime
import pytest
from pydantic import ValidationError

from src.config import load_config, get_active_city_bbox, get_active_city_center
from src.data.schemas import POISchema, FootfallPingSchema, StoreMetricSchema


def test_load_config():
    """Verify that configuration loads successfully and contains required keys."""
    config = load_config()
    assert "project" in config
    assert config["project"]["name"] == "GeoPulse"
    assert "locations" in config
    assert "retail_categories" in config


def test_get_active_city_helpers():
    """Verify active city bounding box and center coordinate helpers."""
    bbox = get_active_city_bbox()
    assert len(bbox) == 4
    assert bbox[0] < bbox[2]  # min_lat < max_lat
    assert bbox[1] < bbox[3]  # min_lon < max_lon

    lat, lon = get_active_city_center()
    assert bbox[0] <= lat <= bbox[2]
    assert bbox[1] <= lon <= bbox[3]


def test_poi_schema_valid():
    """Test POISchema with valid inputs."""
    poi = POISchema(
        id="osm_node_101",
        name="Third Wave Coffee",
        category="cafe",
        latitude=12.9345,
        longitude=77.6212,
        city="Bengaluru",
        rating=4.5,
        brand="Third Wave Coffee",
    )
    assert poi.name == "Third Wave Coffee"
    assert poi.latitude == 12.9345
    assert poi.rating == 4.5


def test_poi_schema_invalid_lat():
    """Test POISchema rejects invalid latitude out of bounds."""
    with pytest.raises(ValidationError):
        POISchema(
            id="bad_lat",
            name="Invalid Store",
            category="apparel",
            latitude=112.9345,  # Invalid latitude > 90
            longitude=77.6212,
            city="Bengaluru",
        )


def test_footfall_ping_schema():
    """Test FootfallPingSchema validation."""
    ping = FootfallPingSchema(
        ping_id="ping_001",
        device_id="dev_a1b2c3",
        timestamp=datetime.now(),
        latitude=12.9350,
        longitude=77.6240,
        dwell_time_minutes=35.5,
        zone_id="hex_88618925d3fffff",
        is_weekend=False,
    )
    assert ping.dwell_time_minutes == 35.5
    assert ping.is_weekend is False


def test_store_metric_schema():
    """Test StoreMetricSchema with conversion rate constraints."""
    metric = StoreMetricSchema(
        store_id="store_kor_01",
        store_name="Zara Koramangala",
        category="apparel",
        latitude=12.9360,
        longitude=77.6250,
        daily_footfall=1420,
        avg_dwell_minutes=42.3,
        passerby_count=850,
        shopper_count=570,
        conversion_rate=0.401,
    )
    assert metric.conversion_rate == 0.401

    # Should raise error if conversion_rate > 1.0
    with pytest.raises(ValidationError):
        StoreMetricSchema(
            store_id="store_kor_01",
            store_name="Zara Koramangala",
            category="apparel",
            latitude=12.9360,
            longitude=77.6250,
            daily_footfall=1420,
            avg_dwell_minutes=42.3,
            passerby_count=850,
            shopper_count=570,
            conversion_rate=1.45,  # Invalid
        )
