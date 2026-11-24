"""
Day 3 Cleaning Pipeline Execution Script.
Runs cleaning, temporal enrichment, audit reporting, and Parquet conversion.
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.cleaner import (
    clean_pois,
    clean_telemetry,
    save_processed_datasets,
    save_data_quality_report,
)


def run_pipeline():
    print("=" * 60)
    print("GeoPulse Day 3: Data Cleaning & Preprocessing Pipeline")
    print("=" * 60)

    # 1. Clean Points of Interest
    print("\n[Step 1/4] Auditing and Cleaning POIs...")
    df_pois, poi_audit = clean_pois()
    print(f" -> Retained {len(df_pois)}/{poi_audit['initial_record_count']} POIs ({poi_audit['completeness_pct']}%)")

    # 2. Clean Mobility Telemetry
    print("\n[Step 2/4] Auditing and Cleaning Mobility Telemetry...")
    df_telemetry, telemetry_audit = clean_telemetry()
    print(
        f" -> Retained {len(df_telemetry):,}/{telemetry_audit['initial_record_count']:,} pings "
        f"({telemetry_audit['retention_rate_pct']}%)"
    )
    print(f" -> Identified {telemetry_audit['shopper_count']:,} Engaged Shoppers vs {telemetry_audit['passerby_count']:,} Passersby")

    # 3. Convert to Parquet Format
    print("\n[Step 3/4] Exporting to Columnar Apache Parquet...")
    poi_parquet, telemetry_parquet = save_processed_datasets(df_pois, df_telemetry)
    print(f" -> Saved POIs: {poi_parquet}")
    print(f" -> Saved Telemetry: {telemetry_parquet}")

    # 4. Generate Quality Audit Report
    print("\n[Step 4/4] Writing Data Quality Report...")
    report_file = save_data_quality_report(poi_audit, telemetry_audit)
    print(f" -> Saved Quality Audit Report: {report_file}")

    print("\nDay 3 Data Cleaning Pipeline completed successfully!")


if __name__ == "__main__":
    run_pipeline()
