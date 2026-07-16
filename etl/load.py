"""
ETL Load Module
===============
Saves clean data into PostgreSQL tables and HDFS (partitioned Parquet files).
"""
import os
import sys
import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.logger import get_logger
from utils.helpers import load_config
from storage.postgres import PostgreSQLClient
from storage.hdfs import HDFSClient

logger = get_logger("etl_load")
load_dotenv()

class DataLoader:
    def __init__(self, config_path: str = "./config/config.yaml"):
        self.config = load_config(config_path)
        self.postgres = PostgreSQLClient(config_path)
        self.hdfs = HDFSClient(config_path)
        
    def load_to_postgres(self, df: pd.DataFrame, table_name: str, if_exists: str = "append"):
        """Loads a pandas dataframe to a PostgreSQL table."""
        if df.empty:
            logger.warning(f"Empty dataframe passed for table {table_name}. Load skipped.")
            return
        logger.info(f"Loading {len(df)} rows into PostgreSQL table: {table_name}")
        self.postgres.load_dataframe(df, table_name, if_exists)
        
    def load_to_hdfs(self, df: pd.DataFrame, relative_path: str):
        """Loads a pandas dataframe to HDFS as Parquet."""
        if df.empty:
            logger.warning("Empty dataframe passed for HDFS. Load skipped.")
            return
            
        # Standard partitioning: year/month/day
        # We can extract from df's timestamp if present, otherwise use today's date
        if 'timestamp' in df.columns:
            ts_col = pd.to_datetime(df['timestamp'])
            years = ts_col.dt.year.unique()
            months = ts_col.dt.month.unique()
            days = ts_col.dt.day.unique()
            
            # Simple fallback to dynamic directory structures
            for y in years:
                for m in months:
                    for d in days:
                        sub_df = df[
                            (ts_col.dt.year == y) &
                            (ts_col.dt.month == m) &
                            (ts_col.dt.day == d)
                        ]
                        if not sub_df.empty:
                            partition_path = f"{relative_path}/year={y}/month={m}/day={d}"
                            self.hdfs.write_parquet(sub_df, partition_path)
        else:
            self.hdfs.write_parquet(df, relative_path)
            
        logger.info(f"Successfully loaded data to HDFS at path: {relative_path}")
