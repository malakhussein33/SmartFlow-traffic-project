"""
Helper Utilities Module
=======================
Contains utility functions for geo-calculations, string normalization,
time evaluation, congestion indexing, and configs.
"""
import os
import yaml
import math
from typing import Dict, Any, Callable
from datetime import datetime, timezone
import time
from dotenv import load_dotenv
from utils.logger import get_logger

logger = get_logger("helpers")

# Load environment variables
load_dotenv()

def load_config(config_path: str = "./config/config.yaml") -> Dict[str, Any]:
    """Loads YAML config and overrides with environment variables where applicable."""
    if not os.path.exists(config_path):
        # Fallback to local search or create simple dict
        logger.warning(f"Config path {config_path} not found. Using default structure.")
        return {}
        
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        
    # Override with Env Vars if present
    if os.getenv("KAFKA_BOOTSTRAP_SERVERS"):
        config['kafka']['bootstrap_servers'] = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    if os.getenv("POSTGRES_HOST"):
        config['postgres']['host'] = os.getenv("POSTGRES_HOST")
    if os.getenv("POSTGRES_PORT"):
        config['postgres']['port'] = int(os.getenv("POSTGRES_PORT"))
    if os.getenv("POSTGRES_DB"):
        config['postgres']['db'] = os.getenv("POSTGRES_DB")
    if os.getenv("POSTGRES_USER"):
        config['postgres']['user'] = os.getenv("POSTGRES_USER")
    if os.getenv("POSTGRES_PASSWORD"):
        config['postgres']['password'] = os.getenv("POSTGRES_PASSWORD")
    if os.getenv("HDFS_NAMENODE"):
        config['hdfs']['namenode'] = os.getenv("HDFS_NAMENODE")
    if os.getenv("HDFS_PORT"):
        config['hdfs']['port'] = int(os.getenv("HDFS_PORT"))
        
    return config

def validate_coordinates(lat: float, lon: float) -> bool:
    """Validates if latitude and longitude ranges are valid."""
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0

def normalize_road_name(name: str) -> str:
    """Cleans and normalizes road names."""
    if not name:
        return ""
    return " ".join(name.strip().split()).title()

def calculate_traffic_density(vehicle_count: int, road_length: float, lanes: int = 1) -> float:
    """Calculates traffic density as vehicle count per kilometer per lane."""
    if road_length <= 0 or lanes <= 0:
        return 0.0
    return float(vehicle_count) / (road_length * lanes)

def calculate_congestion_index(avg_speed: float, speed_limit: float) -> float:
    """Calculates congestion index as a value between 0 (none) and 1 (extreme)."""
    if speed_limit <= 0:
        return 0.0
    if avg_speed >= speed_limit:
        return 0.0
    # Lower speed -> higher congestion
    index = 1.0 - (avg_speed / speed_limit)
    return max(0.0, min(1.0, index))

def get_congestion_level(congestion_index: float) -> str:
    """Classifies congestion index into LOW, MEDIUM, HIGH, or CRITICAL."""
    if congestion_index < 0.25:
        return "LOW"
    elif congestion_index < 0.5:
        return "MEDIUM"
    elif congestion_index < 0.75:
        return "HIGH"
    else:
        return "CRITICAL"

def is_rush_hour(hour: int) -> bool:
    """Returns True if the hour falls into typical morning or evening rush hours."""
    return (7 <= hour <= 9) or (17 <= hour <= 19)

def is_weekend(day_of_week: int) -> bool:
    """Returns True if day of week is Friday or Saturday (typical Egyptian weekend)."""
    # 4 is Friday, 5 is Saturday (assuming Monday is 0)
    # Let's support 4 (Friday), 5 (Saturday) and 6 (Sunday) depending on standard
    # Typically in Egypt it's Friday (4) and Saturday (5)
    return day_of_week in [4, 5]

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates distance between two points in km using Haversine formula."""
    R = 6371.0 # earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def retry_with_backoff(max_retries: int = 5, backoff_factor: float = 1.5) -> Callable:
    """Decorator to retry a function execution with exponential backoff on exceptions."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            retries = 0
            delay = 1.0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries. Error: {e}")
                        raise e
                    logger.warning(f"Function {func.__name__} failed. Retrying in {delay:.2f}s... Error: {e}")
                    time.sleep(delay)
                    delay *= backoff_factor
        return wrapper
    return decorator

def format_timestamp(ts: datetime) -> str:
    """Formats datetime to ISO 8601 string with UTC indicator."""
    return ts.replace(tzinfo=timezone.utc).isoformat()

def parse_timestamp(ts_str: str) -> datetime:
    """Parses ISO 8601 string back to datetime object."""
    return datetime.fromisoformat(ts_str)
