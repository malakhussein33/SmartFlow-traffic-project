"""
Data Ingestion Orchestrator
===========================
Orchestrates CSV sample file ingestion and sets up storage tables.
"""
import os
import sys
import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.helpers import load_config
from utils.logger import get_logger
from storage.postgres import PostgreSQLClient
from storage.hdfs import HDFSClient

logger = get_logger("data_ingestion")
load_dotenv()

class DataIngestionOrchestrator:
    def __init__(self, config_path: str = "./config/config.yaml"):
        self.config = load_config(config_path)
        self.db = PostgreSQLClient(config_path)
        self.hdfs = HDFSClient(config_path)
        self.sample_dir = self.config['data']['sample_dir']
        
    def bootstrap_database(self):
        logger.info("Bootstrapping database with schema and seed values...")
        # Since we use docker entrypoint, this is a fallback validation step
        schema_path = "./database/schema.sql"
        seed_path = "./database/seed.sql"
        
        if os.path.exists(schema_path):
            with open(schema_path, "r") as f:
                self.db.execute_write(f.read())
            logger.info("Schema applied successfully.")
            
        if os.path.exists(seed_path):
            with open(seed_path, "r") as f:
                # Execution can fail if already seeded
                try:
                    self.db.execute_write(f.read())
                    logger.info("Seed data applied successfully.")
                except Exception as e:
                    logger.warning(f"Seeding skipped or failed (likely already applied): {e}")

    def ingest_sample_csv_to_postgres(self):
        logger.info("Ingesting historical CSVs to PostgreSQL...")
        
        roads_file = os.path.join(self.sample_dir, "historical_roads.csv")
        sensors_file = os.path.join(self.sample_dir, "historical_sensors.csv")
        weather_file = os.path.join(self.sample_dir, "historical_weather.csv")
        traffic_file = os.path.join(self.sample_dir, "historical_traffic.csv")
        rides_file = os.path.join(self.sample_dir, "historical_ride_requests.csv")
        
        # Ingest Roads
        if os.path.exists(roads_file):
            df = pd.read_csv(roads_file)
            # Create engine and write
            self.db.load_dataframe(df, "roads", if_exists="append")
            logger.info(f"Loaded {len(df)} roads into database.")
            
        # Ingest Sensors
        if os.path.exists(sensors_file):
            df = pd.read_csv(sensors_file)
            self.db.load_dataframe(df, "sensor_locations", if_exists="append")
            logger.info(f"Loaded {len(df)} sensor locations.")
            
        # Ingest Weather
        if os.path.exists(weather_file):
            df = pd.read_csv(weather_file)
            self.db.load_dataframe(df, "weather_data", if_exists="append")
            logger.info(f"Loaded {len(df)} weather history records.")
            
        # Ingest Traffic
        if os.path.exists(traffic_file):
            df = pd.read_csv(traffic_file)
            self.db.load_dataframe(df, "traffic_events", if_exists="append")
            logger.info(f"Loaded {len(df)} traffic events.")
            
        # Ingest Ride Requests
        if os.path.exists(rides_file):
            df = pd.read_csv(rides_file)
            self.db.load_dataframe(df, "ride_requests", if_exists="append")
            logger.info(f"Loaded {len(df)} ride requests.")

    def run_ingestion(self):
        self.bootstrap_database()
        self.ingest_sample_csv_to_postgres()
        logger.info("Data Ingestion Orchestration Complete.")

if __name__ == '__main__':
    orchestrator = DataIngestionOrchestrator()
    orchestrator.run_ingestion()
