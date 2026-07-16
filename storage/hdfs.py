"""
HDFS Storage Client
===================
Manages parquet file read/write operations to HDFS.
Includes a local filesystem fallback for simplified development environments.
"""
import os
import sys
import pandas as pd
from hdfs import InsecureClient
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.helpers import load_config
from utils.logger import get_logger

logger = get_logger("storage_hdfs")
load_dotenv()

class HDFSClient:
    def __init__(self, config_path: str = "./config/config.yaml"):
        self.config = load_config(config_path)
        self.h_cfg = self.config['hdfs']
        self.raw_dir = self.config['data']['raw_dir']
        self.processed_dir = self.config['data']['processed_dir']
        
        # Insecure client setup
        self.hdfs_url = f"http://{self.h_cfg['namenode']}:{self.h_cfg['port']}"
        self.use_hdfs = False
        
        try:
            self.client = InsecureClient(self.hdfs_url, user=self.h_cfg['user'])
            # Verify connectivity
            self.client.status("/")
            self.use_hdfs = True
            logger.info(f"HDFS Client successfully connected to {self.hdfs_url}")
        except Exception as e:
            logger.warning(f"Could not connect to HDFS namenode: {e}. Falling back to local filesystem storage.")
            self.client = None
            
    def write_parquet(self, df: pd.DataFrame, relative_path: str):
        """Writes a pandas DataFrame to a parquet file (HDFS or local fallback)."""
        # Ensure path is cleaned
        clean_path = relative_path.lstrip("/")
        
        if self.use_hdfs:
            hdfs_full_path = f"{self.h_cfg['base_path']}/{clean_path}/data.parquet"
            try:
                # Create parent directory if needed
                self.client.makedirs(os.path.dirname(hdfs_full_path))
                with self.client.write(hdfs_full_path, overwrite=True) as writer:
                    df.to_parquet(writer, compression=self.config['data']['parquet_compression'].lower())
                logger.info(f"DataFrame loaded to HDFS: {hdfs_full_path}")
            except Exception as e:
                logger.error(f"Failed to write parquet to HDFS: {e}")
                self._write_local(df, clean_path)
        else:
            self._write_local(df, clean_path)

    def _write_local(self, df: pd.DataFrame, clean_path: str):
        local_dir = os.path.join(self.processed_dir, clean_path)
        os.makedirs(local_dir, exist_ok=True)
        local_file = os.path.join(local_dir, "data.parquet")
        df.to_parquet(local_file, index=False, compression=self.config['data']['parquet_compression'].lower())
        logger.info(f"DataFrame loaded to Local Storage: {local_file}")

    def read_parquet(self, relative_path: str) -> pd.DataFrame:
        """Reads a parquet file (from HDFS or local fallback)."""
        clean_path = relative_path.lstrip("/")
        
        if self.use_hdfs:
            hdfs_full_path = f"{self.h_cfg['base_path']}/{clean_path}/data.parquet"
            try:
                with self.client.read(hdfs_full_path) as reader:
                    return pd.read_parquet(reader)
            except Exception as e:
                logger.error(f"Failed to read parquet from HDFS: {e}")
                return self._read_local(clean_path)
        else:
            return self._read_local(clean_path)

    def _read_local(self, clean_path: str) -> pd.DataFrame:
        local_file = os.path.join(self.processed_dir, clean_path, "data.parquet")
        if not os.path.exists(local_file):
            logger.warning(f"Local parquet path does not exist: {local_file}")
            return pd.DataFrame()
        return pd.read_parquet(local_file)

    def health_check(self) -> bool:
        if self.use_hdfs and self.client:
            try:
                self.client.status("/")
                return True
            except Exception:
                return False
        return False
