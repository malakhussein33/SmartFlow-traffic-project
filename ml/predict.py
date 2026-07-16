"""
Model Prediction Service
========================
Provides interfaces to load trained models and predict future vehicle traffic volumes.
"""
import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.helpers import load_config, get_congestion_level, calculate_congestion_index
from utils.logger import get_logger

logger = get_logger("ml_predict")
load_dotenv()

class TrafficPredictor:
    def __init__(self, config_path: str = "./config/config.yaml"):
        self.config = load_config(config_path)
        self.model_dir = self.config['ml']['model_dir']
        
        self.scaler_path = os.path.join(self.model_dir, "scaler.joblib")
        self.model_path = os.path.join(self.model_dir, "traffic_demand_model.joblib")
        self.metadata_path = os.path.join(self.model_dir, "model_metadata.json")
        
        self.scaler = None
        self.model = None
        self.metadata = None
        self._load_model_artifacts()
        
    def _load_model_artifacts(self):
        """Loads serialized model files if available, otherwise logs warnings."""
        if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
            try:
                self.scaler = joblib.load(self.scaler_path)
                self.model = joblib.load(self.model_path)
                
                if os.path.exists(self.metadata_path):
                    with open(self.metadata_path, 'r') as f:
                        self.metadata = json.load(f)
                logger.info("Model artifacts loaded successfully.")
            except Exception as e:
                logger.error(f"Error loading model artifacts: {e}")
        else:
            logger.warning("ML Model artifacts not found. Please train models first to get accurate predictions.")

    def predict_vehicle_count(self, input_features: Dict[str, Any]) -> float:
        """Predicts vehicle count for a given road and conditions."""
        if not self.model or not self.scaler:
            # Simple heuristic fallback if ML model is not trained yet
            return self._fallback_prediction(input_features)
            
        try:
            # Build feature vector matching features list in train.py
            # ['hour', 'day_of_week', 'month', 'is_weekend', 'is_rush_hour',
            # 'temperature_celsius', 'humidity_percent', 'average_speed_kmh', 'num_lanes', 'speed_limit_kmh']
            feat_list = [
                input_features.get('hour', 12),
                input_features.get('day_of_week', 0),
                input_features.get('month', 6),
                int(input_features.get('is_weekend', False)),
                int(input_features.get('is_rush_hour', False)),
                input_features.get('temperature_celsius', 25.0),
                input_features.get('humidity_percent', 50.0),
                input_features.get('average_speed_kmh', 60.0),
                input_features.get('num_lanes', 3),
                input_features.get('speed_limit_kmh', 60)
            ]
            
            feat_arr = np.array([feat_list])
            scaled_feat = self.scaler.transform(feat_arr)
            prediction = self.model.predict(scaled_feat)[0]
            
            return float(max(0.0, prediction))
        except Exception as e:
            logger.error(f"Failed to make ML prediction: {e}")
            return self._fallback_prediction(input_features)

    def predict_congestion(self, input_features: Dict[str, Any]) -> Dict[str, Any]:
        """Predicts vehicle count, congestion index, and congestion label."""
        vehicle_count = self.predict_vehicle_count(input_features)
        
        # Calculate potential average speed based on predicted vehicle count
        speed_limit = input_features.get('speed_limit_kmh', 60)
        lanes = input_features.get('num_lanes', 3)
        base_capacity = lanes * 150
        
        speed_factor = 1.0 - (vehicle_count / (base_capacity * 1.5))
        speed_factor = max(0.1, min(1.1, speed_factor))
        predicted_speed = speed_limit * speed_factor
        
        congestion_index = calculate_congestion_index(predicted_speed, speed_limit)
        congestion_level = get_congestion_level(congestion_index)
        
        return {
            "predicted_vehicle_count": int(vehicle_count),
            "predicted_average_speed": round(predicted_speed, 1),
            "predicted_congestion_index": round(congestion_index, 2),
            "predicted_congestion_level": congestion_level
        }

    def _fallback_prediction(self, features: Dict[str, Any]) -> float:
        """Rule-based simulation fallback if ML model is unavailable."""
        hour = features.get('hour', 12)
        lanes = features.get('num_lanes', 3)
        is_rush = features.get('is_rush_hour', False)
        is_wknd = features.get('is_weekend', False)
        
        base_capacity = lanes * 150
        factor = 0.5
        if is_rush:
            factor = 0.95
        elif is_wknd:
            factor = 0.35
            
        if 23 <= hour or hour <= 5:
            factor = 0.1
            
        return float(int(base_capacity * factor))
