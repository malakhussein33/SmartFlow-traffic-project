"""
Unit Tests - Machine Learning Modules
====================================
Tests fallback heuristics and predictor methods.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ml.predict import TrafficPredictor
from ml.evaluate import ModelEvaluator

class TestMLMetricsAndPredictions(unittest.TestCase):
    def setUp(self):
        self.predictor = TrafficPredictor()
        self.predictor.model = None
        self.predictor.scaler = None
        self.evaluator = ModelEvaluator()

    def test_fallback_prediction(self):
        features = {
            "hour": 8, # Rush hour
            "num_lanes": 3,
            "is_rush_hour": True,
            "is_weekend": False
        }
        pred_vehicles = self.predictor.predict_vehicle_count(features)
        # Cap = 3 * 150 = 450. Rush factor = 0.95 -> 427 vehicles
        self.assertEqual(int(pred_vehicles), 427)

    def test_predict_congestion(self):
        features = {
            "hour": 8,
            "num_lanes": 3,
            "is_rush_hour": True,
            "is_weekend": False,
            "speed_limit_kmh": 60
        }
        res = self.predictor.predict_congestion(features)
        self.assertIn("predicted_vehicle_count", res)
        self.assertIn("predicted_congestion_level", res)
        self.assertEqual(res['predicted_congestion_level'], "HIGH") # 427 vehicles is HIGH congestion under scaled capacity

if __name__ == '__main__':
    unittest.main()
