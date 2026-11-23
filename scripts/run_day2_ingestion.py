"""
End-to-End Execution Script for Day 2 Ingestion Pipeline.
Extracts POIs, runs realistic mobility simulation, and writes raw datasets.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.osm_loader import fetch_pois, save_pois_to_raw
from src.data.mobility_generator import generate_mobility_telemetry, save_telemetry_to_raw


def run_pipeline():
    print("=" * 60)
    print("GeoPulse Day 2: Ingestion Pipeline Execution")
    print("=" * 60)

    # 1. Fetch Points of Interest
    print("\n[Step 1/3] Extracting Retail Points of Interest...")
    pois = fetch_pois()
    poi_file = save_pois_to_raw(pois, filename="osm_pois_raw.json")
    print(f" -> Successfully saved {len(pois)} POIs to {poi_file}")

    # 2. Generate Mobility Telemetry
    print("\n[Step 2/3] Simulating Mobility Telemetry (Diurnal & Weekend)...")
    telemetry_df = generate_mobility_telemetry(pois, num_devices=450, days=14)
    telemetry_file = save_telemetry_to_raw(telemetry_df, filename="mobility_telemetry.csv")
    print(f" -> Successfully saved {len(telemetry_df)} telemetry pings to {telemetry_file}")

    # 3. Print Quick Ingestion Audit
    print("\n[Step 3/3] Data Quality & Distribution Summary:")
    print(f"  • Total Retail POIs: {len(pois)}")
    print(f"  • Categories: {sorted(list(set(p.category for p in pois)))}")
    print(f"  • Total Footfall Records: {len(telemetry_df):,}")
    print(f"  • Weekend Pings: {(telemetry_df['is_weekend'] == True).sum():,} ({((telemetry_df['is_weekend'] == True).mean()*100):.1f}%)")
    print(f"  • Mean Dwell Time: {telemetry_df['dwell_time_minutes'].mean():.2f} mins")
    print(f"  • Median Dwell Time: {telemetry_df['dwell_time_minutes'].median():.2f} mins")
    print("\nDay 2 Ingestion Pipeline completed successfully!")


if __name__ == "__main__":
    run_pipeline()
