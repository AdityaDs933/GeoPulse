"""
Day 5 Execution Script: Spatial Hex-Binning & Catchment Zone Analysis.
Assigns hex cells to all telemetry pings and POIs, computes density metrics,
calculates catchment radii, identifies cannibalization overlaps, and exports GeoJSON.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.config import ROOT_DIR
from src.features.spatial_grid import assign_hex_cells, compute_hex_density
from src.features.catchment import (
    compute_poi_footfall_radius,
    compute_catchment_overlap,
    export_catchment_geojson,
)


def run_pipeline():
    print("=" * 60)
    print("GeoPulse Day 5: Spatial Hex-Binning & Catchment Zone Analysis")
    print("=" * 60)

    proc_dir = ROOT_DIR / "data" / "processed"

    # 1. Load clean datasets
    print("\n[Step 1/6] Loading Clean Parquet Data...")
    df_telemetry = pd.read_parquet(proc_dir / "clean_mobility_telemetry.parquet")
    df_pois = pd.read_parquet(proc_dir / "clean_pois.parquet")
    print(f" -> Telemetry: {len(df_telemetry):,} records | POIs: {len(df_pois)} locations")

    # 2. Hex-bin telemetry at Resolution 9 (~174m)
    print("\n[Step 2/6] Assigning Hexagonal Spatial Cells (Resolution 9)...")
    df_telemetry = assign_hex_cells(df_telemetry, resolution=9, output_col="hex_id_r9")
    n_cells = df_telemetry["hex_id_r9"].nunique()
    print(f" -> Mapped {len(df_telemetry):,} pings into {n_cells} hex cells")

    # 3. Hex-bin POIs
    print("\n[Step 3/6] Assigning Hex Cells to POIs...")
    df_pois = assign_hex_cells(df_pois, resolution=9, output_col="hex_id_r9")

    # 4. Compute hex density
    print("\n[Step 4/6] Computing Per-Cell Density Metrics...")
    hex_density = compute_hex_density(df_telemetry, hex_col="hex_id_r9")
    print(f" -> Top-3 Hotspot Cells:")
    for _, row in hex_density.head(3).iterrows():
        print(f"    {row['hex_id_r9']}: {row['total_pings']} pings, "
              f"shopper ratio {row['shopper_ratio']:.1%}, "
              f"density rank {row['footfall_density_rank']:.0f}th pctl")

    # Save hex density
    hex_density.to_parquet(proc_dir / "hex_density_r9.parquet", index=False)
    hex_density.to_csv(proc_dir / "hex_density_r9.csv", index=False)

    # 5. Catchment radius analysis
    print("\n[Step 5/6] Computing Catchment Radii & Cannibalization Overlaps...")
    df_catchment = compute_poi_footfall_radius(df_telemetry, df_pois)
    df_overlap = compute_catchment_overlap(df_catchment)

    df_catchment.to_csv(proc_dir / "poi_catchment_radii.csv", index=False)
    if len(df_overlap):
        df_overlap.to_csv(proc_dir / "catchment_overlap_pairs.csv", index=False)

    print(f" -> Catchment Summary:")
    print(f"    Mean Primary Radius:   {df_catchment['primary_radius_m'].mean():.1f} m")
    print(f"    Mean Secondary Radius: {df_catchment['secondary_radius_m'].mean():.1f} m")
    print(f"    Overlapping Pairs:     {len(df_overlap)}")
    if len(df_overlap):
        high_risk = df_overlap[df_overlap["risk_level"] == "High"]
        print(f"    High-Risk Cannibalizations: {len(high_risk)}")
        for _, pair in high_risk.head(3).iterrows():
            print(f"      {pair['store_a']} ↔ {pair['store_b']}: "
                  f"{pair['distance_m']:.0f}m apart, overlap {pair['overlap_ratio']:.1%}")

    # 6. Export GeoJSON for dashboard
    print("\n[Step 6/6] Exporting Catchment Zone GeoJSON...")
    geojson_path = export_catchment_geojson(df_catchment)
    print(f" -> Saved: {geojson_path}")

    # Save updated telemetry with hex IDs
    df_telemetry.to_parquet(proc_dir / "clean_mobility_telemetry.parquet", index=False)

    print("\nDay 5 Spatial Analysis completed successfully!")


if __name__ == "__main__":
    run_pipeline()
