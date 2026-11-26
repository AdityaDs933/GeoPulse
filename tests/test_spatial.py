"""
Unit tests for Day 5: Spatial Hex-Binning & Catchment Zone Analysis.
"""

import json
import math
from pathlib import Path

import pandas as pd
import pytest

from src.features.spatial_grid import (
    haversine_distance,
    assign_hex_cells,
    compute_hex_density,
    _hex_cell_id,
)
from src.features.catchment import (
    compute_poi_footfall_radius,
    compute_catchment_overlap,
    export_catchment_geojson,
)


# ── Spatial Grid Tests ──────────────────────────────────────────────

def test_haversine_known_distance():
    """Verify haversine against a known city-pair distance."""
    # Bengaluru to Pune ≈ 735 km (great-circle distance)
    dist = haversine_distance(12.9716, 77.5946, 18.5204, 73.8567)
    assert 730_000 < dist < 745_000


def test_haversine_same_point():
    """Distance from a point to itself must be zero."""
    assert haversine_distance(12.935, 77.625, 12.935, 77.625) == 0.0


def test_hex_cell_deterministic():
    """Same coordinates must always produce the same hex ID."""
    id1 = _hex_cell_id(12.935, 77.625, resolution=9)
    id2 = _hex_cell_id(12.935, 77.625, resolution=9)
    assert id1 == id2
    assert id1.startswith("hex_r9_")


def test_hex_cell_different_resolutions():
    """Different resolutions must produce distinct cell IDs."""
    id8 = _hex_cell_id(12.935, 77.625, resolution=8)
    id9 = _hex_cell_id(12.935, 77.625, resolution=9)
    assert "r8" in id8
    assert "r9" in id9


def test_assign_hex_cells():
    """Verify hex assignment adds column to DataFrame."""
    df = pd.DataFrame({
        "latitude": [12.934, 12.935, 12.980],
        "longitude": [77.625, 77.625, 77.650],
    })
    result = assign_hex_cells(df, resolution=9, output_col="hex_id")
    assert "hex_id" in result.columns
    assert len(result) == 3
    # First two points are very close → should share a cell
    # Third point is ~5 km away → different cell
    assert result.iloc[2]["hex_id"] != result.iloc[0]["hex_id"]


def test_compute_hex_density():
    """Verify density aggregation returns expected columns."""
    df = pd.DataFrame({
        "latitude": [12.935] * 10 + [12.980] * 3,
        "longitude": [77.625] * 10 + [77.650] * 3,
        "dwell_time_minutes": [5.0] * 7 + [30.0] * 3 + [5.0] * 3,
        "device_id": [f"d{i}" for i in range(13)],
        "visitor_type": ["Passerby"] * 7 + ["Engaged Shopper"] * 3 + ["Passerby"] * 3,
        "hex_id": ["hex_A"] * 10 + ["hex_B"] * 3,
    })
    density = compute_hex_density(df, hex_col="hex_id")
    assert len(density) == 2
    top = density.iloc[0]
    assert top["total_pings"] == 10
    assert top["shopper_ratio"] == 0.3  # 3/10


# ── Catchment Tests ─────────────────────────────────────────────────

@pytest.fixture
def sample_catchment_data():
    """Two POIs with attributed telemetry pings at known distances."""
    pois = pd.DataFrame([
        {"id": "poi_a", "name": "Cafe Alpha", "category": "cafe",
         "latitude": 12.9350, "longitude": 77.6250},
        {"id": "poi_b", "name": "Cafe Beta", "category": "cafe",
         "latitude": 12.9355, "longitude": 77.6253},  # ~60 m away
    ])
    # Create pings clustered around each POI
    telemetry = pd.DataFrame([
        {"ping_id": f"p{i}", "device_id": f"d{i}",
         "latitude": 12.9350 + (i * 0.00005), "longitude": 77.6250,
         "dwell_time_minutes": 10.0, "nearest_poi_id": "poi_a",
         "visitor_type": "Passerby"}
        for i in range(20)
    ] + [
        {"ping_id": f"q{i}", "device_id": f"d{20+i}",
         "latitude": 12.9355 + (i * 0.00004), "longitude": 77.6253,
         "dwell_time_minutes": 25.0, "nearest_poi_id": "poi_b",
         "visitor_type": "Engaged Shopper"}
        for i in range(15)
    ])
    return telemetry, pois


def test_compute_poi_footfall_radius(sample_catchment_data):
    """Verify catchment radii are computed for each POI."""
    telemetry, pois = sample_catchment_data
    result = compute_poi_footfall_radius(telemetry, pois)
    assert len(result) == 2
    assert "primary_radius_m" in result.columns
    assert "secondary_radius_m" in result.columns
    assert "tertiary_radius_m" in result.columns
    # Primary must be <= Secondary <= Tertiary
    for _, row in result.iterrows():
        assert row["primary_radius_m"] <= row["secondary_radius_m"]
        assert row["secondary_radius_m"] <= row["tertiary_radius_m"]


def test_compute_catchment_overlap(sample_catchment_data):
    """Verify that nearby same-category stores produce overlap records."""
    telemetry, pois = sample_catchment_data
    catchment = compute_poi_footfall_radius(telemetry, pois)
    overlap = compute_catchment_overlap(catchment)
    # The two cafes are ~60m apart; they should overlap
    assert len(overlap) >= 1
    assert "overlap_ratio" in overlap.columns
    assert overlap.iloc[0]["overlap_ratio"] > 0


def test_export_catchment_geojson(tmp_path, sample_catchment_data):
    """Verify GeoJSON export produces valid FeatureCollection."""
    telemetry, pois = sample_catchment_data
    catchment = compute_poi_footfall_radius(telemetry, pois)
    out_file = tmp_path / "test_catchment.geojson"
    result_path = export_catchment_geojson(catchment, output_path=out_file)
    assert result_path.exists()

    with open(result_path) as f:
        geojson = json.load(f)

    assert geojson["type"] == "FeatureCollection"
    # 2 POIs × 3 zones = 6 features
    assert len(geojson["features"]) == 6
    # Each feature must be a Polygon
    for feat in geojson["features"]:
        assert feat["geometry"]["type"] == "Polygon"
        coords = feat["geometry"]["coordinates"][0]
        assert len(coords) > 10  # Circle approximation
