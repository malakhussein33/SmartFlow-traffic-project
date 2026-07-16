"""
ETL Transform Module
====================
Performs cleaning, normalization, and feature engineering on traffic datasets.
"""
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.helpers import (
    load_config, validate_coordinates, normalize_road_name,
    calculate_traffic_density, calculate_congestion_index, get_congestion_level,
    is_rush_hour, is_weekend
)
from utils.logger import get_logger

logger = get_logger("etl_transform")
load_dotenv()

class DataTransformer:
    def __init__(self, config_path: str = "./config/config.yaml"):
        self.config = load_config(config_path)

    def clean_traffic_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Removes nulls, duplicates, and invalid speeds/coordinates."""
        if df.empty:
            return df
            
        logger.info("Cleaning traffic data...")
        initial_len = len(df)
        
        # Drop duplicates
        df = df.drop_duplicates()
        
        # Drop null values in core fields
        df = df.dropna(subset=['sensor_id', 'vehicle_count', 'average_speed_kmh', 'timestamp'])
        
        # Validate coordinates if present
        if 'latitude' in df.columns and 'longitude' in df.columns:
            valid_coords = df.apply(lambda r: validate_coordinates(r['latitude'], r['longitude']), axis=1)
            df = df[valid_coords]
            
        # Filter negative values and unrealistic vehicle counts/speeds
        df = df[(df['vehicle_count'] >= 0) & (df['average_speed_kmh'] >= 0)]
        df = df[df['average_speed_kmh'] <= 200] # Cap speed limit at 200 kmh
        
        logger.info(f"Cleaned traffic data: {initial_len} -> {len(df)} rows.")
        return df

    def transform_traffic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enriches the traffic dataset with time components, road lengths, and congestion features."""
        if df.empty:
            return df
            
        logger.info("Performing feature engineering on traffic data...")
        df = df.copy()
        
        # Normalize road name
        if 'road_name' in df.columns:
            df['road_name'] = df['road_name'].apply(normalize_road_name)
            
        # Parse timestamp and extract time features
        # Support string timestamps
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['month'] = df['timestamp'].dt.month
        df['is_weekend'] = df['day_of_week'].apply(is_weekend)
        df['is_rush_hour'] = df['hour'].apply(is_rush_hour)
        
        # Road length and lanes mapping (fallback if missing)
        # Using typical lane values from config
        if 'num_lanes' not in df.columns:
            df['num_lanes'] = 3
        if 'length_km' not in df.columns:
            df['length_km'] = 5.0
        if 'speed_limit_kmh' not in df.columns:
            df['speed_limit_kmh'] = 60
            
        # Calculate derived indexes
        df['traffic_density'] = df.apply(
            lambda r: calculate_traffic_density(r['vehicle_count'], r['length_km'], r['num_lanes']),
            axis=1
        )
        df['congestion_index'] = df.apply(
            lambda r: calculate_congestion_index(r['average_speed_kmh'], r['speed_limit_kmh']),
            axis=1
        )
        df['congestion_level'] = df['congestion_index'].apply(get_congestion_level)
        
        return df

    def run_pipeline(self, df: pd.DataFrame) -> pd.DataFrame:
        """Runs the entire transform pipeline."""
        df = self.clean_traffic_data(df)
        df = self.transform_traffic_features(df)
        return df
