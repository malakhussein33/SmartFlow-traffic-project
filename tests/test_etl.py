"""
Unit Tests - ETL Pipeline
==========================
Verifies pandas DataFrame cleaning and enrichment transformations in transformer step.
"""
import os
import sys
import unittest
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from etl.transform import DataTransformer

class TestETLPipeline(unittest.TestCase):
    def setUp(self):
        self.transformer = DataTransformer()
        self.raw_data = pd.DataFrame([
            {
                "sensor_id": "SENSOR_TEST_01",
                "road_name": "  ring road cairo  ",
                "latitude": 30.0444,
                "longitude": 31.2357,
                "vehicle_count": 100,
                "average_speed_kmh": 40.0,
                "timestamp": "2026-07-15T12:00:00Z"
            },
            # Null record
            {
                "sensor_id": None,
                "road_name": "Tahrir",
                "latitude": 30.0444,
                "longitude": 31.2357,
                "vehicle_count": 100,
                "average_speed_kmh": None,
                "timestamp": "2026-07-15T12:00:00Z"
            },
            # Invalid coordinate record
            {
                "sensor_id": "SENSOR_TEST_02",
                "road_name": "Haram",
                "latitude": 100.0,  # Invalid
                "longitude": 31.2357,
                "vehicle_count": 50,
                "average_speed_kmh": 60.0,
                "timestamp": "2026-07-15T12:00:00Z"
            }
        ])

    def test_clean_traffic_data(self):
        cleaned_df = self.transformer.clean_traffic_data(self.raw_data)
        # Drops null row and invalid coordinate row
        self.assertEqual(len(cleaned_df), 1)
        self.assertEqual(cleaned_df.iloc[0]['sensor_id'], "SENSOR_TEST_01")

    def test_transform_traffic_features(self):
        cleaned_df = self.transformer.clean_traffic_data(self.raw_data)
        transformed_df = self.transformer.transform_traffic_features(cleaned_df)
        
        self.assertIn("hour", transformed_df.columns)
        self.assertIn("is_weekend", transformed_df.columns)
        self.assertIn("traffic_density", transformed_df.columns)
        self.assertIn("congestion_level", transformed_df.columns)
        
        # Verify normalization
        self.assertEqual(transformed_df.iloc[0]['road_name'], "Ring Road Cairo")

if __name__ == '__main__':
    unittest.main()
