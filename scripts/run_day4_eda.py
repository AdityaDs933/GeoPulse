"""
Execution script for Day 4: Exploratory Data Analysis & Statistical Profiling.
Loads clean parquet datasets, computes statistical summaries, exports publication figures,
and creates the statistical profile JSON report.
"""

import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from src.config import ROOT_DIR
from src.visualization.eda_visualizer import generate_all_eda_visualizations


def run_pipeline():
    print("=" * 60)
    print("GeoPulse Day 4: Exploratory Data Analysis & Statistical Profiling")
    print("=" * 60)

    # 1. Load clean processed Parquet datasets
    proc_dir = ROOT_DIR / "data" / "processed"
    telemetry_path = proc_dir / "clean_mobility_telemetry.parquet"
    pois_path = proc_dir / "clean_pois.parquet"

    print("\n[Step 1/3] Loading Clean Columnar Parquet Data...")
    df_telemetry = pd.read_parquet(telemetry_path)
    df_pois = pd.read_parquet(pois_path)
    print(f" -> Telemetry: {len(df_telemetry):,} rows loaded.")
    print(f" -> POIs: {len(df_pois):,} retail locations loaded.")

    # 2. Generate publication-quality figures
    print("\n[Step 2/3] Rendering Publication-Grade Visualizations...")
    figures_dir = ROOT_DIR / "reports" / "figures"
    figure_paths, summary = generate_all_eda_visualizations(df_telemetry, df_pois, figures_dir)
    for name, path in figure_paths.items():
        print(f" -> Created figure: {path.name}")

    # 3. Export Statistical Summary Report
    print("\n[Step 3/3] Saving Statistical Profiling Summary...")
    report_file = ROOT_DIR / "reports" / "eda_statistical_summary.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f" -> Saved statistical summary: {report_file}")

    # Print Key Metrics
    print("\n" + "-" * 40)
    print("Key Analytical Insights:")
    print(f" • Peak Hour: {summary['temporal_dynamics']['peak_hour_24h']}:00 (Ratio: {summary['temporal_dynamics']['peak_to_trough_ratio']}x over trough)")
    print(f" • Weekend Uplift Multiplier: {summary['temporal_dynamics']['weekend_uplift_multiplier']}x")
    print(f" • Dwell Skewness: {summary['dwell_time_distribution']['skewness']} (Right-skewed, Bimodal)")
    print(f" • Engaged Shopper Ratio: {summary['dwell_time_distribution']['shopper_ratio']*100:.1f}%")
    print("-" * 40)
    print("\nDay 4 EDA and Profiling completed successfully!")


if __name__ == "__main__":
    run_pipeline()
