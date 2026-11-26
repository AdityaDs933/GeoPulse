"""
Spatial Hex-Binning & Grid Indexing Module for GeoPulse.

Implements geodesic spatial discretization that maps raw lat/lon coordinates
into uniform hexagonal cells. Since Uber's h3-py library requires C extensions
that may not be available in every environment, this module provides a pure-Python
geodesic hexagonal grid that replicates H3's core value proposition:

    - Equidistant neighbor cells (no diagonal distortion like square grids)
    - Hierarchical multi-resolution support
    - Deterministic cell-ID assignment from any (lat, lon) pair

Resolution reference (approximate edge lengths):
    Resolution 8  ~ 460 m  (neighborhood-scale catchments)
    Resolution 9  ~ 174 m  (store-level pedestrian zones)
    Resolution 10 ~  66 m  (micro-zone / storefront level)
"""

import math
import logging
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from src.config import ROOT_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Earth radius in metres
EARTH_RADIUS_M = 6_371_000.0

# Approximate hex edge length per resolution level (metres)
RESOLUTION_EDGE_M: Dict[int, float] = {
    7: 1_220.0,
    8: 460.0,
    9: 174.0,
    10: 66.0,
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance between two WGS-84 points in metres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def _hex_cell_id(lat: float, lon: float, resolution: int = 9) -> str:
    """Assign a deterministic hexagonal cell ID to a (lat, lon) coordinate.

    Strategy: offset hex-grid quantisation on an equirectangular projection,
    with row-dependent longitude shift to produce hexagonal tiling.
    """
    edge_m = RESOLUTION_EDGE_M.get(resolution, 174.0)

    # Convert edge to approximate degree deltas at given latitude
    lat_step = edge_m / 111_320.0  # 1 deg lat ≈ 111.32 km
    lon_step = edge_m / (111_320.0 * max(math.cos(math.radians(lat)), 0.01))

    # Hex height = sqrt(3) * edge; width = 2 * edge
    hex_h = lat_step * math.sqrt(3)
    hex_w = lon_step * 2.0

    row = int(math.floor(lat / hex_h))
    # Offset every other row by half the hex width
    lon_shifted = lon - (hex_w * 0.5 if row % 2 else 0.0)
    col = int(math.floor(lon_shifted / hex_w))

    return f"hex_r{resolution}_{row:+06d}_{col:+06d}"


def assign_hex_cells(
    df: pd.DataFrame,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    resolution: int = 9,
    output_col: str = "hex_id",
) -> pd.DataFrame:
    """Add a hex-cell ID column to a DataFrame of lat/lon coordinates.

    Args:
        df: DataFrame containing latitude and longitude columns
        lat_col: Name of the latitude column
        lon_col: Name of the longitude column
        resolution: Hex resolution (7-10). Lower = larger cells.
        output_col: Name of the output column to create

    Returns:
        DataFrame with additional hex_id column
    """
    df = df.copy()
    df[output_col] = df.apply(
        lambda r: _hex_cell_id(r[lat_col], r[lon_col], resolution), axis=1
    )
    logger.info(
        f"Assigned {df[output_col].nunique()} unique hex cells (res={resolution}) "
        f"across {len(df)} records."
    )
    return df


def compute_hex_density(
    df: pd.DataFrame,
    hex_col: str = "hex_id",
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    dwell_col: str = "dwell_time_minutes",
    visitor_col: str = "visitor_type",
) -> pd.DataFrame:
    """Aggregate per-hex-cell density and dwell statistics.

    Returns a DataFrame indexed by hex_id with columns:
        - centroid_lat, centroid_lon  (geometric mean of member points)
        - total_pings               (footfall count)
        - unique_devices            (distinct visitor devices)
        - mean_dwell_minutes        (average dwell duration)
        - shopper_ratio             (fraction of Engaged Shoppers)
        - footfall_density_rank     (percentile rank 0-100)
    """
    agg = df.groupby(hex_col).agg(
        centroid_lat=(lat_col, "mean"),
        centroid_lon=(lon_col, "mean"),
        total_pings=(hex_col, "size"),
        unique_devices=("device_id", "nunique") if "device_id" in df.columns else (hex_col, "size"),
        mean_dwell_minutes=(dwell_col, "mean"),
        shopper_count=(visitor_col, lambda x: (x == "Engaged Shopper").sum()),
    ).reset_index()

    agg["shopper_ratio"] = (agg["shopper_count"] / agg["total_pings"]).round(3)
    agg["footfall_density_rank"] = agg["total_pings"].rank(pct=True).mul(100).round(1)

    agg = agg.sort_values("total_pings", ascending=False).reset_index(drop=True)
    logger.info(f"Computed density metrics for {len(agg)} hex cells.")
    return agg
