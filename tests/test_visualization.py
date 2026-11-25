"""
Unit tests for Day 4: Exploratory Data Analysis & Visualization.
"""

from pathlib import Path
import pandas as pd
import pytest

from src.visualization.eda_visualizer import (
    compute_statistical_summary,
    generate_all_eda_visualizations,
)


@pytest.fixture
def sample_data():
    """Create lightweight test datasets."""
    telemetry = pd.DataFrame([
        {
            "ping_id": f"p_{i}",
            "device_id": f"dev_{i%5}",
            "hour": 12 if i % 2 == 0 else 19,
            "day_name": "Saturday" if i % 3 == 0 else "Monday",
            "is_weekend": True if i % 3 == 0 else False,
            "dwell_time_minutes": 5.0 if i % 2 == 0 else 35.0,
            "visitor_type": "Passerby" if i % 2 == 0 else "Engaged Shopper",
            "poi_category": "cafe" if i % 2 == 0 else "apparel",
        }
        for i in range(30)
    ])
    pois = pd.DataFrame([
        {"id": "poi_1", "name": "Cafe A", "category": "cafe"},
        {"id": "poi_2", "name": "Shop B", "category": "apparel"},
    ])
    return telemetry, pois


def test_compute_statistical_summary(sample_data):
    """Verify statistical summary computation."""
    df_telemetry, df_pois = sample_data
    summary = compute_statistical_summary(df_telemetry, df_pois)

    assert "record_metrics" in summary
    assert summary["record_metrics"]["total_telemetry_records"] == 30
    assert summary["record_metrics"]["total_retail_pois"] == 2
    assert "dwell_time_distribution" in summary
    assert "temporal_dynamics" in summary
    assert "category_breakdown" in summary


def test_generate_all_eda_visualizations(tmp_path, sample_data):
    """Verify all 4 publication charts are rendered and saved."""
    df_telemetry, df_pois = sample_data
    fig_paths, summary = generate_all_eda_visualizations(df_telemetry, df_pois, tmp_path)

    expected_figs = [
        "01_diurnal_footfall_curve.png",
        "02_dwell_time_bimodal_distribution.png",
        "03_category_footfall_dwell_matrix.png",
        "04_day_of_week_footfall_heatmap.png",
    ]
    for fig_name in expected_figs:
        target = tmp_path / fig_name
        assert target.exists()
        assert target.stat().st_size > 1000  # Valid non-empty PNG
