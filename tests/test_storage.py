"""
Unit Tests - Storage Clients
============================
Verifies database client query structures using MagicMock wrappers.
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from storage.postgres import PostgreSQLClient

class TestStorageIntegration(unittest.TestCase):
    @patch('storage.postgres.create_engine')
    def test_execute_query_returns_dataframe(self, mock_engine):
        # Mock connection and query responses
        mock_conn = MagicMock()
        mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
        
        # We patch pandas read_sql to return a dummy df instead of connecting
        with patch('pandas.read_sql') as mock_read_sql:
            mock_read_sql.return_value = pd.DataFrame([{"id": 1, "name": "Salah Salem"}])
            
            client = PostgreSQLClient()
            df = client.execute_query("SELECT * FROM roads")
            
            self.assertFalse(df.empty)
            self.assertEqual(df.iloc[0]['name'], "Salah Salem")

if __name__ == '__main__':
    unittest.main()
