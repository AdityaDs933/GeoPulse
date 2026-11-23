"""
Mobility Telemetry Generator for GeoPulse.
Simulates realistic high-resolution pedestrian footfall telemetry with:
- Realistic diurnal curves (morning, lunch bump, evening retail peak)
- Weekend traffic multipliers (1.45x)
- Spatial clustering around retail POIs (with realistic GPS noise/drift)
- Bimodal dwell time distributions (transit passersby vs. engaged shoppers)
"""

from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import List, Optional
import numpy as np
import pandas as pd

from src.config import load_config, ROOT_DIR
from src.data.schemas import POISchema, FootfallPingSchema

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# Hourly footfall probability distribution (0 to 23 hours)
HOURLY_PROBABILITIES = [
    0.005, 0.003, 0.002, 0.002, 0.003, 0.008,  # 00:00 - 05:00
    0.020, 0.045, 0.070, 0.065, 0.060, 0.075,  # 06:00 - 11:00 (morning ramp)
    0.095, 0.090, 0.065, 0.060, 0.070, 0.085,  # 12:00 - 17:00 (lunch & afternoon)
    0.110, 0.120, 0.105, 0.075, 0.040, 0.015,  # 18:00 - 23:00 (evening shopping peak)
]
# Normalize probabilities to sum exactly to 1.0
HOURLY_PROBABILITIES = np.array(HOURLY_PROBABILITIES) / np.sum(HOURLY_PROBABILITIES)


def generate_mobility_telemetry(
    pois: List[POISchema],
    num_devices: int = 400,
    days: int = 14,
    start_date: Optional[datetime] = None,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate synthetic but statistically authentic mobility telemetry.

    Args:
        pois: List of retail POIs around which pedestrian traffic clusters
        num_devices: Distinct simulated devices / pedestrian hashes
        days: Duration of the observation window
        start_date: Starting datetime (defaults to 14 days ago)
        seed: Random seed for reproducibility

    Returns:
        Pandas DataFrame containing validated footfall pings
    """
    np.random.seed(seed)
    if start_date is None:
        start_date = datetime(2026, 11, 1, 0, 0, 0)

    pings: List[dict] = []
    ping_counter = 1

    device_pool = [f"dev_{i:04d}_{np.random.randint(1000, 9999)}" for i in range(num_devices)]
    poi_coords = [(p.latitude, p.longitude, p.id, p.category) for p in pois]

    logger.info(f"Generating mobility telemetry: {num_devices} devices across {days} days...")

    for day_offset in range(days):
        current_day = start_date + timedelta(days=day_offset)
        is_weekend = current_day.weekday() >= 5  # Saturday=5, Sunday=6
        daily_multiplier = 1.45 if is_weekend else 1.0

        # Number of footfall events for the day
        base_daily_pings = int(len(pois) * 28 * daily_multiplier)
        daily_pings_count = np.random.poisson(base_daily_pings)

        # Sample hours based on diurnal probability distribution
        sampled_hours = np.random.choice(24, size=daily_pings_count, p=HOURLY_PROBABILITIES)

        for hour in sampled_hours:
            minute = np.random.randint(0, 60)
            second = np.random.randint(0, 60)
            timestamp = current_day.replace(hour=int(hour), minute=int(minute), second=int(second))

            # Pick a target retail POI cluster
            poi_idx = np.random.randint(0, len(poi_coords))
            lat_center, lon_center, poi_id, category = poi_coords[poi_idx]

            # Spatial jitter / GPS drift: Gaussian noise (~20m - 50m, 1 deg ~ 111km -> 0.0003 deg ~ 33m)
            lat_jitter = np.random.normal(0, 0.00035)
            lon_jitter = np.random.normal(0, 0.00035)

            # Dwell time distribution: Bimodal
            # Mode A (Passerby: 60% probability) -> Exponential with mean ~3 mins
            # Mode B (Shopper: 40% probability) -> Lognormal with mean ~32 mins
            is_passerby = np.random.rand() < 0.60
            if is_passerby:
                dwell_mins = float(np.clip(np.random.exponential(scale=3.0), 0.5, 8.0))
            else:
                dwell_mins = float(np.clip(np.random.lognormal(mean=3.4, sigma=0.45), 10.0, 180.0))

            device_id = np.random.choice(device_pool)

            pings.append({
                "ping_id": f"ping_{ping_counter:07d}",
                "device_id": device_id,
                "timestamp": timestamp.isoformat(),
                "latitude": round(lat_center + lat_jitter, 6),
                "longitude": round(lon_center + lon_jitter, 6),
                "dwell_time_minutes": round(dwell_mins, 2),
                "nearest_poi_id": poi_id,
                "poi_category": category,
                "is_weekend": is_weekend,
            })
            ping_counter += 1

    df = pd.DataFrame(pings)
    logger.info(f"Successfully generated {len(df)} mobility footfall pings.")
    return df


def save_telemetry_to_raw(df: pd.DataFrame, filename: str = "mobility_telemetry.csv") -> Path:
    """Save raw mobility telemetry to CSV in data/raw/."""
    raw_dir = ROOT_DIR / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_file = raw_dir / filename
    df.to_csv(out_file, index=False)
    logger.info(f"Saved raw telemetry ({len(df)} rows) to {out_file}")
    return out_file
