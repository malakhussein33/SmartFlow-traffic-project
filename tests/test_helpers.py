"""
Unit Tests - Helpers Module
===========================
Verifies geofencing coordinate filters, normalization, time calculations,
and mathematical distance formulas.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.helpers import (
    validate_coordinates, normalize_road_name, calculate_traffic_density,
    calculate_congestion_index, get_congestion_level, is_rush_hour,
    is_weekend, haversine_distance
)

class TestHelperUtilities(unittest.TestCase):
    def test_validate_coordinates(self):
        self.assertTrue(validate_coordinates(30.0444, 31.2357))
        self.assertFalse(validate_coordinates(95.0, 31.2357))
        self.assertFalse(validate_coordinates(30.0444, -190.0))

    def test_normalize_road_name(self):
        self.assertEqual(normalize_road_name("  ring road cairo  "), "Ring Road Cairo")
        self.assertEqual(normalize_road_name("salah salem"), "Salah Salem")

    def test_calculate_traffic_density(self):
        self.assertEqual(calculate_traffic_density(100, 2.0, 2), 25.0)
        self.assertEqual(calculate_traffic_density(0, 5.0, 3), 0.0)
        self.assertEqual(calculate_traffic_density(100, 0.0, 1), 0.0)

    def test_calculate_congestion_index(self):
        # average speed higher/equal to speed limit -> no congestion
        self.assertEqual(calculate_congestion_index(80.0, 80.0), 0.0)
        self.assertEqual(calculate_congestion_index(100.0, 80.0), 0.0)
        # speed is half of limit -> 0.5
        self.assertEqual(calculate_congestion_index(40.0, 80.0), 0.5)

    def test_get_congestion_level(self):
        self.assertEqual(get_congestion_level(0.1), "LOW")
        self.assertEqual(get_congestion_level(0.4), "MEDIUM")
        self.assertEqual(get_congestion_level(0.6), "HIGH")
        self.assertEqual(get_congestion_level(0.85), "CRITICAL")

    def test_is_rush_hour(self):
        self.assertTrue(is_rush_hour(8))
        self.assertTrue(is_rush_hour(18))
        self.assertFalse(is_rush_hour(12))

    def test_is_weekend(self):
        # Assuming Friday(4) and Saturday(5)
        self.assertTrue(is_weekend(4))
        self.assertTrue(is_weekend(5))
        self.assertFalse(is_weekend(0)) # Monday

    def test_haversine_distance(self):
        # Cairo center to Giza center
        dist = haversine_distance(30.0444, 31.2357, 30.0131, 31.2089)
        self.assertGreater(dist, 0.0)
        self.assertLess(dist, 10.0)

if __name__ == '__main__':
    unittest.main()
