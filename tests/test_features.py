"""
Unit tests for Day 6: Advanced Mobility Feature Engineering.
"""

import pandas as pd
import numpy as np
import pytest

from src.features.mobility_metrics import (
    compute_dwell_to_passerby_index,
    compute_footfall_volatility,
    compute_temporal_features,
    compute_competitor_density,
    compute_catchment_efficiency,
    compute_repeat_visitor_ratio,
    build_master_feature_matrix,
)


@pytest.fixture
def sample_telemetry():
    """Create test telemetry with known dwell split."""
    rows = []
    for i in range(60):
        rows.append({
            "ping_id": f"p{i}",
            "device_id": f"d{i % 20}",
            "dwell_time_minutes": 5.0 if i < 36 else 30.0,  # 60% passerby, 40% shopper
            "nearest_poi_id": "poi_a" if i < 40 else "poi_b",
            "is_weekend": i % 5 == 0,
            "hour": (10 + i) % 24,
            "date": f"2026-11-{15 + i % 7:02d}",
            "visitor_type": "Passerby" if i < 36 else "Engaged Shopper",
        })
    return pd.DataFrame(rows)


@pytest.fixture
def sample_pois():
    return pd.DataFrame([
        {"id": "poi_a", "name": "Cafe A", "category": "cafe",
         "latitude": 12.9350, "longitude": 77.6250, "rating": 4.5, "brand": "BrandA"},
        {"id": "poi_b", "name": "Cafe B", "category": "cafe",
         "latitude": 12.9352, "longitude": 77.6252, "rating": 4.3, "brand": "BrandB"},
        {"id": "poi_c", "name": "Shop C", "category": "apparel",
         "latitude": 12.9800, "longitude": 77.6500, "rating": 4.0, "brand": "BrandC"},
    ])


@pytest.fixture
def sample_catchment():
    return pd.DataFrame([
        {"poi_id": "poi_a", "total_footfall": 400, "primary_radius_m": 50, "secondary_radius_m": 80, "tertiary_radius_m": 120},
        {"poi_id": "poi_b", "total_footfall": 200, "primary_radius_m": 40, "secondary_radius_m": 60, "tertiary_radius_m": 100},
    ])


def test_dpi_calculation(sample_telemetry):
    """Verify DPI separates shoppers from passersby correctly."""
    result = compute_dwell_to_passerby_index(sample_telemetry)
    assert len(result) == 2
    assert "dpi" in result.columns
    # All values should be between 0 and 1
    assert (result["dpi"] >= 0).all()
    assert (result["dpi"] <= 1).all()


def test_footfall_volatility(sample_telemetry):
    """Verify volatility index is non-negative."""
    result = compute_footfall_volatility(sample_telemetry)
    assert "footfall_volatility_index" in result.columns
    assert (result["footfall_volatility_index"] >= 0).all()


def test_temporal_features(sample_telemetry):
    """Verify temporal KPIs contain expected columns."""
    result = compute_temporal_features(sample_telemetry)
    expected_cols = ["weekend_uplift_ratio", "peak_hour_concentration",
                     "evening_dominance_score", "temporal_coverage_score"]
    for col in expected_cols:
        assert col in result.columns
    # Temporal coverage should be 0-1
    assert (result["temporal_coverage_score"] >= 0).all()
    assert (result["temporal_coverage_score"] <= 1).all()


def test_competitor_density(sample_pois):
    """Verify competitor density finds nearby same-category stores."""
    result = compute_competitor_density(sample_pois, radius_m=300)
    assert len(result) == 3
    # poi_a and poi_b are both cafes ~25m apart → should detect each other
    poi_a_row = result[result["poi_id"] == "poi_a"].iloc[0]
    assert poi_a_row["same_category_competitors"] >= 1


def test_catchment_efficiency(sample_catchment):
    """Verify catchment efficiency is positive."""
    result = compute_catchment_efficiency(sample_catchment)
    assert "catchment_efficiency" in result.columns
    assert (result["catchment_efficiency"] > 0).all()


def test_repeat_visitor_ratio(sample_telemetry):
    """Verify repeat ratio is bounded 0-1."""
    result = compute_repeat_visitor_ratio(sample_telemetry)
    assert "repeat_visitor_ratio" in result.columns
    assert (result["repeat_visitor_ratio"] >= 0).all()
    assert (result["repeat_visitor_ratio"] <= 1).all()


def test_master_feature_matrix(sample_telemetry, sample_pois, sample_catchment):
    """Verify master matrix merges all KPIs and produces suitability score."""
    master = build_master_feature_matrix(sample_telemetry, sample_pois, sample_catchment)
    assert "suitability_score" in master.columns
    assert "dpi" in master.columns
    assert "footfall_volatility_index" in master.columns
    assert "weekend_uplift_ratio" in master.columns
    assert "competitor_density_score" in master.columns
    # Score should be 0-100 range
    assert (master["suitability_score"] >= 0).all()
    assert (master["suitability_score"] <= 100).all()
