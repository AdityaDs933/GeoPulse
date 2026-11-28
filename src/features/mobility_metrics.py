"""
Advanced Mobility Feature Engineering for GeoPulse.

Transforms raw footfall telemetry and spatial catchment data into sophisticated
retail business KPIs. Each metric is designed to answer a specific strategic
question for retail site selection and competitive positioning.

Engineered KPIs:
    1. Dwell-to-Passerby Index (DPI)         — High-intent shopper concentration
    2. Footfall Volatility Index (FVI)        — Traffic stability / predictability
    3. Weekend Uplift Ratio                   — Weekend revenue opportunity
    4. Peak-Hour Concentration Ratio          — Staffing demand intensity
    5. Evening Dominance Score                — After-work shopping potential
    6. Category Diversity Index               — Retail ecosystem richness
    7. Competitor Density Score               — Same-category saturation pressure
    8. Cannibalization Risk Index             — Revenue splitting vulnerability
    9. Catchment Efficiency Score             — Footfall per unit catchment area
   10. Location Accessibility Score           — Proximity to high-density clusters
   11. Temporal Coverage Score                — Active trading hours breadth
   12. Repeat Visitor Ratio                   — Customer loyalty proxy
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.config import ROOT_DIR
from src.features.spatial_grid import haversine_distance

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def compute_dwell_to_passerby_index(
    df_telemetry: pd.DataFrame,
    poi_id_col: str = "nearest_poi_id",
    threshold_minutes: float = 15.0,
) -> pd.DataFrame:
    """Compute Dwell-to-Passerby Index (DPI) per POI.

    DPI = Engaged Shoppers (dwell >= threshold) / Total Detected Devices

    Higher DPI indicates a location that converts foot traffic into genuine
    store visitors — the single most important retail conversion metric.
    """
    grouped = df_telemetry.groupby(poi_id_col).agg(
        total_pings=("ping_id", "count"),
        engaged_shoppers=("dwell_time_minutes", lambda x: (x >= threshold_minutes).sum()),
        mean_dwell_minutes=("dwell_time_minutes", "mean"),
        median_dwell_minutes=("dwell_time_minutes", "median"),
        p90_dwell_minutes=("dwell_time_minutes", lambda x: float(np.percentile(x, 90))),
    ).reset_index()

    grouped.rename(columns={poi_id_col: "poi_id"}, inplace=True)
    grouped["dpi"] = (grouped["engaged_shoppers"] / grouped["total_pings"]).round(4)

    return grouped


def compute_footfall_volatility(
    df_telemetry: pd.DataFrame,
    poi_id_col: str = "nearest_poi_id",
) -> pd.DataFrame:
    """Compute Footfall Volatility Index (FVI) per POI.

    FVI = Coefficient of Variation of daily footfall counts.
    Low FVI → stable, predictable traffic (ideal for inventory planning).
    High FVI → erratic traffic (higher staffing/stock risk).
    """
    daily_counts = (
        df_telemetry.groupby([poi_id_col, "date"])
        .size()
        .reset_index(name="daily_pings")
    )

    volatility = daily_counts.groupby(poi_id_col).agg(
        mean_daily_footfall=("daily_pings", "mean"),
        std_daily_footfall=("daily_pings", "std"),
    ).reset_index()

    volatility.rename(columns={poi_id_col: "poi_id"}, inplace=True)
    volatility["footfall_volatility_index"] = (
        volatility["std_daily_footfall"] / volatility["mean_daily_footfall"].clip(lower=1)
    ).round(4)

    return volatility[["poi_id", "mean_daily_footfall", "std_daily_footfall", "footfall_volatility_index"]]


def compute_temporal_features(
    df_telemetry: pd.DataFrame,
    poi_id_col: str = "nearest_poi_id",
) -> pd.DataFrame:
    """Compute temporal mobility KPIs per POI:
        - Weekend Uplift Ratio
        - Peak-Hour Concentration Ratio
        - Evening Dominance Score (% of traffic in 18:00-22:00)
        - Temporal Coverage Score (number of distinct active hours / 24)
    """
    results = []
    for pid, grp in df_telemetry.groupby(poi_id_col):
        total = len(grp)
        weekend_pings = (grp["is_weekend"] == True).sum()
        weekday_pings = total - weekend_pings

        # Weekend uplift: average weekend daily vs average weekday daily
        # Assume 4 weekend days and 10 weekday days in 14-day window
        weekend_daily = weekend_pings / max(1, 4)
        weekday_daily = weekday_pings / max(1, 10)
        weekend_uplift = round(weekend_daily / max(1, weekday_daily), 3)

        # Peak-hour concentration: top-3 hours share of total
        hourly = grp.groupby("hour").size()
        top3_share = round(float(hourly.nlargest(3).sum()) / max(1, total), 3)

        # Evening dominance
        evening_pings = grp[grp["hour"].between(18, 21)].shape[0]
        evening_score = round(evening_pings / max(1, total), 3)

        # Temporal coverage
        active_hours = grp["hour"].nunique()
        temporal_coverage = round(active_hours / 24.0, 3)

        results.append({
            "poi_id": pid,
            "weekend_uplift_ratio": weekend_uplift,
            "peak_hour_concentration": top3_share,
            "evening_dominance_score": evening_score,
            "temporal_coverage_score": temporal_coverage,
        })

    return pd.DataFrame(results)


def compute_competitor_density(
    df_pois: pd.DataFrame,
    radius_m: float = 300.0,
) -> pd.DataFrame:
    """Compute Competitor Density Score per POI.

    Counts how many same-category and all-category stores fall within
    a given radius. High same-category density = saturation risk.
    """
    results = []
    for i, poi in df_pois.iterrows():
        same_cat = 0
        all_nearby = 0
        for j, other in df_pois.iterrows():
            if poi["id"] == other["id"]:
                continue
            dist = haversine_distance(
                poi["latitude"], poi["longitude"],
                other["latitude"], other["longitude"],
            )
            if dist <= radius_m:
                all_nearby += 1
                if poi["category"] == other["category"]:
                    same_cat += 1

        results.append({
            "poi_id": poi["id"],
            "same_category_competitors": same_cat,
            "all_nearby_stores": all_nearby,
            "competitor_density_score": round(same_cat / max(1, all_nearby), 3),
        })

    return pd.DataFrame(results)


def compute_catchment_efficiency(
    df_catchment: pd.DataFrame,
) -> pd.DataFrame:
    """Compute Catchment Efficiency Score.

    Efficiency = Total Footfall / (π × secondary_radius²)
    Higher efficiency means more customers packed into a smaller trade area.
    """
    import math
    df = df_catchment[["poi_id", "total_footfall", "primary_radius_m", "secondary_radius_m"]].copy()
    df["catchment_area_sqm"] = (math.pi * df["secondary_radius_m"] ** 2).round(1)
    df["catchment_efficiency"] = (
        df["total_footfall"] / df["catchment_area_sqm"].clip(lower=1)
    ).round(6)
    return df[["poi_id", "catchment_area_sqm", "catchment_efficiency"]]


def compute_repeat_visitor_ratio(
    df_telemetry: pd.DataFrame,
    poi_id_col: str = "nearest_poi_id",
) -> pd.DataFrame:
    """Compute Repeat Visitor Ratio per POI.

    Repeat ratio = 1 - (unique_devices / total_pings)
    Higher ratio indicates customer loyalty and habitual visits.
    """
    grouped = df_telemetry.groupby(poi_id_col).agg(
        total_pings=("ping_id", "count"),
        unique_devices=("device_id", "nunique"),
    ).reset_index()

    grouped.rename(columns={poi_id_col: "poi_id"}, inplace=True)
    grouped["repeat_visitor_ratio"] = (
        1 - grouped["unique_devices"] / grouped["total_pings"]
    ).round(4)

    return grouped[["poi_id", "unique_devices", "repeat_visitor_ratio"]]


def build_master_feature_matrix(
    df_telemetry: pd.DataFrame,
    df_pois: pd.DataFrame,
    df_catchment: pd.DataFrame,
) -> pd.DataFrame:
    """Assemble the unified Master Retail Feature Matrix by joining all KPIs.

    Returns a single DataFrame with one row per POI and 15+ engineered features,
    ready for ML model training on Day 7.
    """
    logger.info("Building Master Retail Feature Matrix...")

    # 1. Dwell-to-Passerby Index
    dpi = compute_dwell_to_passerby_index(df_telemetry)

    # 2. Footfall Volatility Index
    volatility = compute_footfall_volatility(df_telemetry)

    # 3. Temporal Features
    temporal = compute_temporal_features(df_telemetry)

    # 4. Competitor Density
    competitor = compute_competitor_density(df_pois)

    # 5. Catchment Efficiency
    efficiency = compute_catchment_efficiency(df_catchment)

    # 6. Repeat Visitor Ratio
    repeat = compute_repeat_visitor_ratio(df_telemetry)

    # --- Merge everything on poi_id ---
    master = dpi.copy()
    for feat_df in [volatility, temporal, competitor, efficiency, repeat]:
        master = master.merge(feat_df, on="poi_id", how="left")

    # Merge POI metadata
    poi_meta = df_pois[["id", "name", "category", "latitude", "longitude", "rating", "brand"]].copy()
    poi_meta.rename(columns={"id": "poi_id"}, inplace=True)
    master = master.merge(poi_meta, on="poi_id", how="left")

    # Merge catchment radii
    catch_cols = df_catchment[["poi_id", "primary_radius_m", "secondary_radius_m", "tertiary_radius_m"]].copy()
    master = master.merge(catch_cols, on="poi_id", how="left")

    # --- Composite Suitability Score (Weighted combination) ---
    # Normalize key metrics to 0-1 range and compute weighted score
    def _minmax(s: pd.Series) -> pd.Series:
        rng = s.max() - s.min()
        return (s - s.min()) / rng if rng > 0 else pd.Series(0.5, index=s.index)

    master["norm_dpi"] = _minmax(master["dpi"])
    master["norm_footfall"] = _minmax(master["total_pings"])
    master["norm_efficiency"] = _minmax(master["catchment_efficiency"])
    master["norm_stability"] = 1 - _minmax(master["footfall_volatility_index"])  # Lower volatility = better
    master["norm_evening"] = _minmax(master["evening_dominance_score"])
    master["norm_repeat"] = _minmax(master["repeat_visitor_ratio"])

    # Weighted composite: Suitability Score (0-100)
    master["suitability_score"] = (
        master["norm_dpi"] * 25 +
        master["norm_footfall"] * 20 +
        master["norm_efficiency"] * 15 +
        master["norm_stability"] * 15 +
        master["norm_evening"] * 15 +
        master["norm_repeat"] * 10
    ).round(1)

    # Drop intermediate normalized columns
    norm_cols = [c for c in master.columns if c.startswith("norm_")]
    master.drop(columns=norm_cols, inplace=True)

    logger.info(f"Master Feature Matrix: {master.shape[0]} POIs × {master.shape[1]} features")
    return master
