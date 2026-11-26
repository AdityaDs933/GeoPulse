"""
Retail Catchment Zone Analyzer for GeoPulse.

Computes trade-area boundaries around each retail POI using distance-decay
footfall analysis. Implements the Huff Gravity Model concept:

    Primary Catchment   (60% of attributed footfall)  — core walk-in zone
    Secondary Catchment (25% of attributed footfall)  — moderate reach zone
    Tertiary Catchment  (15% of attributed footfall)  — extended influence zone

Also calculates store-level catchment overlap to quantify cannibalization risk
between neighbouring retail locations.
"""

import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.config import ROOT_DIR
from src.features.spatial_grid import haversine_distance

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def compute_poi_footfall_radius(
    df_telemetry: pd.DataFrame,
    df_pois: pd.DataFrame,
    poi_id_col: str = "nearest_poi_id",
    percentiles: Tuple[float, ...] = (0.60, 0.85, 1.00),
) -> pd.DataFrame:
    """Calculate distance-based catchment radii per POI.

    For each POI, computes the distance from the POI centroid to every
    attributed telemetry ping, then determines the radius that captures
    the specified cumulative percentiles of footfall.

    Args:
        df_telemetry: Cleaned mobility telemetry with nearest_poi_id
        df_pois: POI master dataset
        poi_id_col: Column linking pings to their nearest POI
        percentiles: Cumulative footfall fractions for Primary, Secondary, Tertiary

    Returns:
        DataFrame with columns: poi_id, name, category, lat, lon,
        total_footfall, primary_radius_m, secondary_radius_m, tertiary_radius_m
    """
    results = []

    for _, poi in df_pois.iterrows():
        pid = poi["id"]
        poi_lat, poi_lon = poi["latitude"], poi["longitude"]

        # Get all pings attributed to this POI
        mask = df_telemetry[poi_id_col] == pid
        poi_pings = df_telemetry.loc[mask]

        if len(poi_pings) == 0:
            continue

        # Compute distances from POI centroid to each ping
        distances = poi_pings.apply(
            lambda r: haversine_distance(poi_lat, poi_lon, r["latitude"], r["longitude"]),
            axis=1,
        ).values

        distances_sorted = np.sort(distances)

        # Percentile radii
        radii = []
        for pct in percentiles:
            idx = min(int(np.ceil(pct * len(distances_sorted))) - 1, len(distances_sorted) - 1)
            radii.append(round(float(distances_sorted[idx]), 1))

        results.append({
            "poi_id": pid,
            "name": poi.get("name", pid),
            "category": poi.get("category", "unknown"),
            "latitude": poi_lat,
            "longitude": poi_lon,
            "total_footfall": len(poi_pings),
            "primary_radius_m": radii[0],
            "secondary_radius_m": radii[1],
            "tertiary_radius_m": radii[2],
        })

    df_catchment = pd.DataFrame(results)
    logger.info(f"Computed catchment radii for {len(df_catchment)} POIs.")
    return df_catchment


def compute_catchment_overlap(
    df_catchment: pd.DataFrame,
    radius_col: str = "secondary_radius_m",
) -> pd.DataFrame:
    """Compute pairwise catchment overlap (cannibalization risk) between POIs.

    Two stores overlap when the distance between them is less than the sum of
    their catchment radii. The overlap_ratio is:

        overlap_ratio = max(0, 1 - dist / (r1 + r2))

    Returns a DataFrame of overlapping POI pairs with columns:
        store_a, store_b, distance_m, combined_radius_m, overlap_ratio, risk_level
    """
    records = []
    n = len(df_catchment)

    for i in range(n):
        a = df_catchment.iloc[i]
        for j in range(i + 1, n):
            b = df_catchment.iloc[j]

            dist = haversine_distance(a["latitude"], a["longitude"], b["latitude"], b["longitude"])
            r_sum = a[radius_col] + b[radius_col]

            if dist < r_sum:
                overlap = round(max(0.0, 1.0 - dist / r_sum), 3)
                if overlap < 0.15:
                    risk = "Low"
                elif overlap < 0.40:
                    risk = "Moderate"
                else:
                    risk = "High"

                records.append({
                    "store_a": a["name"],
                    "store_b": b["name"],
                    "category_a": a["category"],
                    "category_b": b["category"],
                    "distance_m": round(dist, 1),
                    "combined_radius_m": round(r_sum, 1),
                    "overlap_ratio": overlap,
                    "risk_level": risk,
                })

    df_overlap = pd.DataFrame(records)
    if len(df_overlap):
        df_overlap = df_overlap.sort_values("overlap_ratio", ascending=False).reset_index(drop=True)
    logger.info(f"Found {len(df_overlap)} overlapping catchment pairs.")
    return df_overlap


def export_catchment_geojson(
    df_catchment: pd.DataFrame,
    output_path: Optional[Path] = None,
    num_circle_points: int = 36,
) -> Path:
    """Export catchment zones as GeoJSON FeatureCollection with circular polygons.

    Each POI generates three concentric circle features (Primary, Secondary, Tertiary).
    """
    if output_path is None:
        output_path = ROOT_DIR / "data" / "processed" / "catchment_zones.geojson"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    features: List[Dict[str, Any]] = []

    zone_configs = [
        ("primary_radius_m", "Primary (60%)", "#0284C7", 0.35),
        ("secondary_radius_m", "Secondary (85%)", "#0EA5E9", 0.20),
        ("tertiary_radius_m", "Tertiary (100%)", "#7DD3FC", 0.10),
    ]

    for _, row in df_catchment.iterrows():
        lat, lon = row["latitude"], row["longitude"]

        for radius_col, zone_label, color, opacity in zone_configs:
            radius_m = row[radius_col]
            # Generate circle polygon points
            coords = []
            for k in range(num_circle_points + 1):
                angle = 2 * math.pi * k / num_circle_points
                dlat = (radius_m / 111_320.0) * math.cos(angle)
                dlon = (radius_m / (111_320.0 * max(math.cos(math.radians(lat)), 0.01))) * math.sin(angle)
                coords.append([round(lon + dlon, 6), round(lat + dlat, 6)])

            feature = {
                "type": "Feature",
                "properties": {
                    "poi_id": row["poi_id"],
                    "name": row["name"],
                    "category": row["category"],
                    "zone": zone_label,
                    "radius_m": radius_m,
                    "total_footfall": int(row["total_footfall"]),
                    "color": color,
                    "opacity": opacity,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords],
                },
            }
            features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)

    logger.info(f"Exported {len(features)} catchment zone polygons to {output_path}")
    return output_path
