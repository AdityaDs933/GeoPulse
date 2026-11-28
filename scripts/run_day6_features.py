"""
Day 6 Execution Script: Advanced Mobility Feature Engineering.
Computes 12+ retail KPIs, assembles the Master Feature Matrix, and saves results.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.config import ROOT_DIR
from src.features.mobility_metrics import (
    compute_dwell_to_passerby_index,
    compute_footfall_volatility,
    compute_temporal_features,
    compute_competitor_density,
    compute_catchment_efficiency,
    compute_repeat_visitor_ratio,
    build_master_feature_matrix,
)


def run_pipeline():
    print("=" * 60)
    print("GeoPulse Day 6: Advanced Mobility Feature Engineering")
    print("=" * 60)

    proc_dir = ROOT_DIR / "data" / "processed"

    # 1. Load datasets
    print("\n[Step 1/4] Loading Clean Parquet Data...")
    df_telemetry = pd.read_parquet(proc_dir / "clean_mobility_telemetry.parquet")
    df_pois = pd.read_parquet(proc_dir / "clean_pois.parquet")
    df_catchment = pd.read_csv(proc_dir / "poi_catchment_radii.csv")
    print(f" -> Telemetry: {len(df_telemetry):,} | POIs: {len(df_pois)} | Catchments: {len(df_catchment)}")

    # 2. Individual KPI Previews
    print("\n[Step 2/4] Computing Individual KPIs...")

    dpi = compute_dwell_to_passerby_index(df_telemetry)
    print(f"\n  Dwell-to-Passerby Index (DPI):")
    top3 = dpi.nlargest(3, "dpi")
    for _, r in top3.iterrows():
        print(f"    {r['poi_id']}: DPI={r['dpi']:.3f} ({r['engaged_shoppers']}/{r['total_pings']} shoppers)")

    vol = compute_footfall_volatility(df_telemetry)
    most_stable = vol.nsmallest(2, "footfall_volatility_index")
    print(f"\n  Most Stable Footfall (Low Volatility):")
    for _, r in most_stable.iterrows():
        print(f"    {r['poi_id']}: FVI={r['footfall_volatility_index']:.3f} (avg {r['mean_daily_footfall']:.0f}/day)")

    comp = compute_competitor_density(df_pois)
    most_competitive = comp.nlargest(2, "same_category_competitors")
    print(f"\n  Highest Competitor Density:")
    for _, r in most_competitive.iterrows():
        print(f"    {r['poi_id']}: {r['same_category_competitors']} same-cat rivals within 300m")

    # 3. Build Master Feature Matrix
    print("\n[Step 3/4] Assembling Master Feature Matrix...")
    master = build_master_feature_matrix(df_telemetry, df_pois, df_catchment)

    master.to_parquet(proc_dir / "retail_features_master.parquet", index=False)
    master.to_csv(proc_dir / "retail_features_master.csv", index=False)

    print(f" -> Saved: {master.shape[0]} POIs × {master.shape[1]} features")
    print(f" -> Feature columns: {list(master.columns)}")

    # 4. Suitability Score Leaderboard
    print("\n[Step 4/4] Retail Site Suitability Leaderboard:")
    print("-" * 70)
    leaderboard = master[["poi_id", "name", "category", "suitability_score", "dpi", "total_pings"]].sort_values(
        "suitability_score", ascending=False
    )
    for rank, (_, r) in enumerate(leaderboard.iterrows(), 1):
        print(f"  #{rank:2d}  Score: {r['suitability_score']:5.1f}  |  DPI: {r['dpi']:.3f}  |  "
              f"Footfall: {r['total_pings']:4d}  |  {r['name']}")
    print("-" * 70)

    print("\nDay 6 Feature Engineering completed successfully!")


if __name__ == "__main__":
    run_pipeline()
