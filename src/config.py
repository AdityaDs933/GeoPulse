"""
Configuration Loader Module for GeoPulse.
Loads project parameters, paths, and bounding boxes safely from YAML.
"""

from pathlib import Path
from typing import Any, Dict, List
import yaml


# Root directory of the repository
ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config" / "config.yaml"


def load_config(config_file: Path = CONFIG_PATH) -> Dict[str, Any]:
    """Load and parse the project configuration YAML file.

    Args:
        config_file: Path to config.yaml

    Returns:
        Dictionary containing project settings
    """
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found at: {config_file}")

    with open(config_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def get_active_city_bbox() -> List[float]:
    """Retrieve bounding box for active city [min_lat, min_lon, max_lat, max_lon]."""
    config = load_config()
    active_city = config["locations"]["active_city"]
    return config["locations"]["cities"][active_city]["bbox"]


def get_active_city_center() -> tuple[float, float]:
    """Retrieve (lat, lon) center coordinates for active city."""
    config = load_config()
    active_city = config["locations"]["active_city"]
    city_data = config["locations"]["cities"][active_city]
    return city_data["center_lat"], city_data["center_lon"]
