"""
Unit and integration tests for Day 2: Ingestion & Mobility Generation.
"""

from datetime import datetime
import pandas as pd
import pytest

from src.data.osm_loader import fetch_pois, build_overpass_query, parse_overpass_elements
from src.data.mobility_generator import generate_mobility_telemetry, HOURLY_PROBABILITIES
from src.data.schemas import POISchema, FootfallPingSchema


def test_build_overpass_query():
    """Verify Overpass QL query string formatting."""
    bbox = [12.915, 77.605, 12.985, 77.655]
    query = build_overpass_query(bbox)
    assert "[out:json]" in query
    assert "12.915,77.605,12.985,77.655" in query
    assert "cafe" in query


def test_fetch_pois():
    """Verify that POIs are extracted and validated against POISchema."""
    pois = fetch_pois("bengaluru")
    assert len(pois) >= 10
    for p in pois:
        assert isinstance(p, POISchema)
        assert p.latitude > 0
        assert p.longitude > 0
        assert len(p.name) > 0


def test_mobility_telemetry_generation():
    """Verify generated mobility telemetry respects statistical and schema contracts."""
    sample_pois = [
        POISchema(
            id="test_01",
            name="Sample Cafe",
            category="cafe",
            latitude=12.9348,
            longitude=77.6253,
            city="Bengaluru",
        )
    ]
    df = generate_mobility_telemetry(sample_pois, num_devices=50, days=3, seed=123)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 50

    # Required columns
    expected_cols = [
        "ping_id", "device_id", "timestamp", "latitude", "longitude",
        "dwell_time_minutes", "nearest_poi_id", "poi_category", "is_weekend"
    ]
    for col in expected_cols:
        assert col in df.columns

    # Check dwell time validity
    assert (df["dwell_time_minutes"] >= 0.5).all()
    assert (df["dwell_time_minutes"] <= 180.0).all()

    # Verify each ping can be validated by FootfallPingSchema
    first_row = df.iloc[0].to_dict()
    first_row["timestamp"] = datetime.fromisoformat(first_row["timestamp"])
    ping = FootfallPingSchema(**first_row)
    assert ping.ping_id == first_row["ping_id"]


def test_hourly_probabilities():
    """Ensure diurnal hourly probabilities sum to 1.0 and evening peak is highest."""
    assert len(HOURLY_PROBABILITIES) == 24
    assert pytest.approx(float(HOURLY_PROBABILITIES.sum()), rel=1e-5) == 1.0
    # Evening peak (18-20h) should be higher than early morning (2-4h)
    assert HOURLY_PROBABILITIES[19] > HOURLY_PROBABILITIES[3]
