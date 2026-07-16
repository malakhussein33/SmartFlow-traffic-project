"""
Model Training Script
=====================
Loads traffic historical records, trains Random Forest, Gradient Boosting,
Linear Regression, and XGBoost regressor models, evaluates targets, and saves the best model.
"""
import os
import sys
import pandas as pd
import numpy as np
import joblib
import json
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
import xgboost as xgb
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.helpers import load_config
from utils.logger import get_logger
from ml.evaluate import ModelEvaluator

logger = get_logger("ml_train")
load_dotenv()

class TrafficMLTrainer:
    def __init__(self, config_path: str = "./config/config.yaml"):
        self.config = load_config(config_path)
        self.model_dir = self.config['ml']['model_dir']
        self.sample_dir = self.config['data']['sample_dir']
        os.makedirs(self.model_dir, exist_ok=True)
        
    def load_data(self) -> pd.DataFrame:
        """Loads historical traffic events merged with road metrics and weather."""
        traffic_path = os.path.join(self.sample_dir, "historical_traffic.csv")
        roads_path = os.path.join(self.sample_dir, "historical_roads.csv")
        weather_path = os.path.join(self.sample_dir, "historical_weather.csv")
        
        if not os.path.exists(traffic_path) or not os.path.exists(roads_path) or not os.path.exists(weather_path):
            logger.error("Historical CSV data not found. Please run historical simulator first.")
            raise FileNotFoundError("Historical data files are missing.")
            
        traffic_df = pd.read_csv(traffic_path)
        roads_df = pd.read_csv(roads_path)
        weather_df = pd.read_csv(weather_path)
        
        # Merge datasets
        df = pd.merge(traffic_df, roads_df, on="road_id")
        df = pd.merge(df, weather_df, on="weather_id", suffixes=("", "_weather"))
        logger.info(f"Loaded training dataset containing {len(df)} rows.")
        return df
        
    def prepare_features(self, df: pd.DataFrame):
        """Processes categorization structures and normalizes inputs."""
        # Target: vehicle_count (predict future demand)
        # Features: hour, road_id, temperature_celsius, humidity_percent, average_speed_kmh, is_weekend, is_rush_hour
        
        # Merge weather details from the table if needed, otherwise use the direct sensor weather fields
        # In our simulator we already have temperature and humidity in the traffic dataset
        # If columns are named slightly differently from raw vs historical, standardize them:
        if 'temperature' in df.columns:
            df['temperature_celsius'] = df['temperature']
        if 'humidity' in df.columns:
            df['humidity_percent'] = df['humidity']
            
        feature_cols = [
            'hour', 'day_of_week', 'month', 'is_weekend', 'is_rush_hour',
            'temperature_celsius', 'humidity_percent', 'average_speed_kmh', 'num_lanes', 'speed_limit_kmh'
        ]
        
        # Drop rows missing values in key targets/features
        df = df.dropna(subset=feature_cols + ['vehicle_count'])
        
        X = df[feature_cols].copy()
        y = df['vehicle_count'].copy()
        
        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        return X_scaled, y, feature_cols, scaler

    def run_training_pipeline(self):
        df = self.load_data()
        X, y, features, scaler = self.prepare_features(df)
        
        # Train / Test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, 
            test_size=self.config['ml']['test_size'], 
            random_state=self.config['ml']['random_state']
        )
        
        logger.info(f"Split completed. Training rows: {len(X_train)}, Testing rows: {len(X_test)}")
        
        evaluator = ModelEvaluator()
        trained_models = {}
        comparison_results = {}
        
        # 1. Linear Regression
        logger.info("Training Linear Regression model...")
        lr = LinearRegression()
        lr.fit(X_train, y_train)
        trained_models['linear_regression'] = lr
        comparison_results['linear_regression'] = evaluator.evaluate_regression(lr, X_test, y_test)
        
        # 2. Random Forest
        logger.info("Training Random Forest regressor...")
        rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        rf.fit(X_train, y_train)
        trained_models['random_forest'] = rf
        comparison_results['random_forest'] = evaluator.evaluate_regression(rf, X_test, y_test)
        
        # 3. Gradient Boosting Regressor
        logger.info("Training Gradient Boosting regressor...")
        gb = GradientBoostingRegressor(n_estimators=100, random_state=42)
        gb.fit(X_train, y_train)
        trained_models['gradient_boosting'] = gb
        comparison_results['gradient_boosting'] = evaluator.evaluate_regression(gb, X_test, y_test)
        
        # 4. XGBoost
        logger.info("Training XGBoost regressor...")
        xg_reg = xgb.XGBRegressor(objective ='reg:squarederror', colsample_bytree = 0.3, learning_rate = 0.1,
                    max_depth = 5, alpha = 10, n_estimators = 100)
        xg_reg.fit(X_train, y_train)
        trained_models['xgboost'] = xg_reg
        comparison_results['xgboost'] = evaluator.evaluate_regression(xg_reg, X_test, y_test)
        
        # Log comparison summary
        logger.info("Evaluation metrics compared:")
        for name, metrics in comparison_results.items():
            logger.info(f"Model: {name} | RMSE: {metrics['RMSE']:.2f} | MAE: {metrics['MAE']:.2f} | R2: {metrics['R2']:.4f}")
            
        # Select best model based on R2 score
        best_model_name = max(comparison_results, key=lambda k: comparison_results[k]['R2'])
        best_model = trained_models[best_model_name]
        logger.info(f"Best model selected: {best_model_name} with R2={comparison_results[best_model_name]['R2']:.4f}")
        
        # Save scaler and models
        scaler_file = os.path.join(self.model_dir, "scaler.joblib")
        joblib.dump(scaler, scaler_file)
        
        model_file = os.path.join(self.model_dir, "traffic_demand_model.joblib")
        joblib.dump(best_model, model_file)
        
        # Save metadata info
        metadata = {
            "best_algorithm": best_model_name,
            "feature_columns": features,
            "metrics": comparison_results[best_model_name],
            "trained_timestamp": datetime.now().isoformat()
        }
        with open(os.path.join(self.model_dir, "model_metadata.json"), "w") as f:
            json.dump(metadata, f, indent=4)
            
        logger.info("Model artifacts and scalers successfully serialized to storage.")

if __name__ == '__main__':
    trainer = TrafficMLTrainer()
    trainer.run_training_pipeline()
