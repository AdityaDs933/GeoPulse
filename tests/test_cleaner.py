"""
Unit tests for Day 3: Data Cleaning, Quality Auditing, and Storage.
"""

import tempfile
import json
from pathlib import Path
import pandas as pd
import pytest

from src.data.cleaner import clean_pois, clean_telemetry, classify_time_slot, save_processed_datasets


def test_classify_time_slot():
    """Verify time slot classification across operational hours."""
    assert classify_time_slot(8) == "Morning Ramp"
    assert classify_time_slot(13) == "Lunch Rush"
    assert classify_time_slot(16) == "Afternoon Lull"
    assert classify_time_slot(19) == "Evening Shopping Peak"
    assert classify_time_slot(23) == "Night Inactive"
    assert classify_time_slot(3) == "Night Inactive"


def test_clean_pois_dedup_and_bounds(tmp_path):
    """Verify POI cleaning drops out of bounds coordinates and duplicates."""
    raw_data = [
        {"id": "p1", "name": "Valid Cafe", "category": "cafe", "latitude": 12.934, "longitude": 77.625},
        {"id": "p1", "name": "Duplicate Cafe", "category": "cafe", "latitude": 12.934, "longitude": 77.625},  # Duplicate
        {"id": "p2", "name": "Out of Bounds Store", "category": "apparel", "latitude": 28.6139, "longitude": 77.2090},  # Delhi (out of bounds)
    ]
    raw_file = tmp_path / "raw_pois.json"
    with open(raw_file, "w") as f:
        json.dump(raw_data, f)

    df_clean, audit = clean_pois(raw_file)
    assert len(df_clean) == 1
    assert df_clean.iloc[0]["id"] == "p1"
    assert audit["duplicate_count"] == 1
    assert audit["out_of_bounds_dropped"] == 1


def test_clean_telemetry_anomalies(tmp_path):
    """Verify telemetry cleaning filters out negative/extreme dwell times and enriches temporal fields."""
    raw_telemetry = pd.DataFrame([
        {
            "ping_id": "p001",
            "device_id": "d01",
            "timestamp": "2026-11-15T19:30:00",
            "latitude": 12.935,
            "longitude": 77.625,
            "dwell_time_minutes": 25.0,
            "nearest_poi_id": "poi_1",
            "poi_category": "cafe",
            "is_weekend": True,
        },
        {
            "ping_id": "p002",
            "device_id": "d02",
            "timestamp": "2026-11-15T19:30:00",
            "latitude": 12.935,
            "longitude": 77.625,
            "dwell_time_minutes": -5.0,  # Negative dwell anomaly
            "nearest_poi_id": "poi_1",
            "poi_category": "cafe",
            "is_weekend": True,
        },
        {
            "ping_id": "p003",
            "device_id": "d03",
            "timestamp": "2026-11-15T19:30:00",
            "latitude": 12.935,
            "longitude": 77.625,
            "dwell_time_minutes": 1500.0,  # > 24 hours anomaly
            "nearest_poi_id": "poi_1",
            "poi_category": "cafe",
            "is_weekend": True,
        },
    ])
    csv_file = tmp_path / "raw_telemetry.csv"
    raw_telemetry.to_csv(csv_file, index=False)

    df_clean, audit = clean_telemetry(csv_file)
    assert len(df_clean) == 1
    assert df_clean.iloc[0]["ping_id"] == "p001"
    assert audit["anomalous_dwell_dropped"] == 2
    assert "time_slot" in df_clean.columns
    assert df_clean.iloc[0]["time_slot"] == "Evening Shopping Peak"
    assert df_clean.iloc[0]["visitor_type"] == "Engaged Shopper"
