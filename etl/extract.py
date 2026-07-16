"""
ETL Extract Module
==================
Extracts data from CSV files, PostgreSQL databases, and mock streams.
"""
import os
import sys
import pandas as pd
from typing import Optional
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.logger import get_logger
from utils.helpers import load_config
from storage.postgres import PostgreSQLClient

logger = get_logger("etl_extract")
load_dotenv()

class DataExtractor:
    def __init__(self, config_path: str = "./config/config.yaml"):
        self.config = load_config(config_path)
        self.postgres = PostgreSQLClient(config_path)
        
    def extract_from_csv(self, file_path: str) -> pd.DataFrame:
        """Extracts data from a CSV file."""
        if not os.path.exists(file_path):
            logger.error(f"CSV file not found at: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        logger.info(f"Extracting data from CSV: {file_path}")
        return pd.read_csv(file_path)
        
    def extract_from_postgres(self, table_name: str, query: Optional[str] = None) -> pd.DataFrame:
        """Extracts data from PostgreSQL."""
        logger.info(f"Extracting data from Postgres: {table_name}")
        sql_query = query if query else f"SELECT * FROM {table_name}"
        return self.postgres.execute_query(sql_query)
