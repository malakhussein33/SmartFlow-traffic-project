"""
PostgreSQL Storage Client
=========================
Manages connections and transactions using SQLAlchemy engine connection pools.
"""
import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.helpers import load_config
from utils.logger import get_logger

logger = get_logger("storage_postgres")
load_dotenv()

class PostgreSQLClient:
    def __init__(self, config_path: str = "./config/config.yaml"):
        self.config = load_config(config_path)
        self.db_cfg = self.config['postgres']
        self.connection_url = f"postgresql://{self.db_cfg['user']}:{self.db_cfg['password']}@{self.db_cfg['host']}:{self.db_cfg['port']}/{self.db_cfg['db']}"
        self.is_fallback = False
        
        try:
            self.engine = create_engine(
                self.connection_url,
                pool_size=self.db_cfg['pool_size'],
                max_overflow=self.db_cfg['max_overflow'],
                pool_timeout=self.db_cfg['pool_timeout']
            )
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1")).fetchone()
            logger.info("Successfully connected to PostgreSQL database.")
        except Exception as e:
            logger.warning(f"Could not connect to PostgreSQL ({e}). Falling back to local SQLite database.")
            self.is_fallback = True
            self._init_sqlite_fallback()
            
    def _init_sqlite_fallback(self):
        logger.info("Initializing SQLite fallback database...")
        db_file = "./data/sample/local_smartflow.db"
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        self.engine = create_engine(f"sqlite:///{db_file}")
        
        # Check if roads table exists
        try:
            with self.engine.connect() as conn:
                res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='roads'")).fetchone()
                if res is None:
                    self._populate_sqlite_from_csv()
        except Exception as e:
            logger.error(f"Failed to initialize SQLite fallback: {e}")
            
    def _populate_sqlite_from_csv(self):
        logger.info("Populating SQLite tables from historical CSV files...")
        sample_dir = "./data/sample"
        csv_files = {
            "roads": "historical_roads.csv",
            "sensor_locations": "historical_sensors.csv",
            "weather_data": "historical_weather.csv",
            "traffic_events": "historical_traffic.csv",
            "ride_requests": "historical_ride_requests.csv"
        }
        
        for table, csv_name in csv_files.items():
            path = os.path.join(sample_dir, csv_name)
            if os.path.exists(path):
                df = pd.read_csv(path)
                with self.engine.begin() as conn:
                    df.to_sql(table, conn, if_exists="replace", index=False)
                logger.info(f"Loaded {len(df)} rows into SQLite table '{table}'")
                
        # Create views
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    CREATE VIEW IF NOT EXISTS v_current_traffic_status AS
                    SELECT 
                        te.sensor_id,
                        r.road_name,
                        sl.latitude,
                        sl.longitude,
                        te.timestamp,
                        te.vehicle_count,
                        te.average_speed_kmh,
                        te.congestion_index,
                        te.congestion_level,
                        w.weather_condition,
                        w.temperature_celsius
                    FROM traffic_events te
                    JOIN roads r ON te.road_id = r.road_id
                    JOIN sensor_locations sl ON te.sensor_id = sl.sensor_id
                    LEFT JOIN weather_data w ON te.weather_id = w.weather_id
                    GROUP BY te.sensor_id
                    HAVING te.timestamp = MAX(te.timestamp);
                """))
                
                conn.execute(text("""
                    CREATE VIEW IF NOT EXISTS v_road_congestion_summary AS
                    SELECT 
                        r.road_name,
                        r.speed_limit_kmh,
                        ROUND(AVG(te.average_speed_kmh), 2) as avg_speed,
                        ROUND(AVG(te.vehicle_count), 2) as avg_vehicle_count,
                        ROUND(AVG(te.congestion_index), 2) as avg_congestion_index,
                        COUNT(CASE WHEN te.congestion_level = 'CRITICAL' THEN 1 END) as critical_events_count
                    FROM traffic_events te
                    JOIN roads r ON te.road_id = r.road_id
                    GROUP BY r.road_name, r.speed_limit_kmh;
                """))
            logger.info("SQLite views created successfully.")
        except Exception as e:
            logger.error(f"Error creating SQLite views: {e}")
        
    def execute_query(self, query: str, params: dict = None) -> pd.DataFrame:
        """Executes a SELECT query and returns results in a pandas DataFrame."""
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params=params)
                return df
        except Exception as e:
            logger.error(f"Postgres execution failed on SELECT query: {e}")
            raise e
            
    def execute_write(self, ddl_query: str, params: dict = None) -> int:
        """Executes DDL/DML write queries (CREATE, UPDATE, INSERT)."""
        try:
            # Preprocess query for SQLite compatibility if fallback is active
            if self.engine.dialect.name == "sqlite":
                # Replace Postgres specific view replacement syntax
                if "v_current_traffic_status" in ddl_query:
                    parts = ddl_query.split("-- VIEWS FOR STREAMLIT DASHBOARD")
                    ddl_query = parts[0]
                    create_views = """
                        CREATE VIEW IF NOT EXISTS v_current_traffic_status AS
                        SELECT 
                            te.sensor_id,
                            r.road_name,
                            sl.latitude,
                            sl.longitude,
                            te.timestamp,
                            te.vehicle_count,
                            te.average_speed_kmh,
                            te.congestion_index,
                            te.congestion_level,
                            w.weather_condition,
                            w.temperature_celsius
                        FROM traffic_events te
                        JOIN roads r ON te.road_id = r.road_id
                        JOIN sensor_locations sl ON te.sensor_id = sl.sensor_id
                        LEFT JOIN weather_data w ON te.weather_id = w.weather_id
                        GROUP BY te.sensor_id
                        HAVING te.timestamp = MAX(te.timestamp);

                        CREATE VIEW IF NOT EXISTS v_road_congestion_summary AS
                        SELECT 
                            r.road_name,
                            r.speed_limit_kmh,
                            ROUND(AVG(te.average_speed_kmh), 2) as avg_speed,
                            ROUND(AVG(te.vehicle_count), 2) as avg_vehicle_count,
                            ROUND(AVG(te.congestion_index), 2) as avg_congestion_index,
                            COUNT(CASE WHEN te.congestion_level = 'CRITICAL' THEN 1 END) as critical_events_count
                        FROM traffic_events te
                        JOIN roads r ON te.road_id = r.road_id
                        GROUP BY r.road_name, r.speed_limit_kmh;
                    """
                    ddl_query += "\n" + create_views

                # Replace Postgres intervals
                import re
                def replace_interval(match):
                    count = match.group(1)
                    unit = match.group(2).lower()
                    return f"datetime('now', '-{count} {unit}')"
                
                ddl_query = re.sub(r"NOW\(\)\s*-\s*INTERVAL\s*'(\d+)\s+(HOURS|MINUTES)'", replace_interval, ddl_query, flags=re.IGNORECASE)
                ddl_query = ddl_query.replace("NOW()", "datetime('now')")
                ddl_query = ddl_query.replace("TIMESTAMPTZ", "TIMESTAMP")
                ddl_query = ddl_query.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
                ddl_query = ddl_query.replace("SERIAL", "INTEGER")

            with self.engine.begin() as conn:
                if self.engine.dialect.name == "sqlite" and ";" in ddl_query:
                    # SQLite executescript handles multiple statements separated by semicolons
                    dbapi_conn = conn.connection.dbapi_connection if hasattr(conn.connection, 'dbapi_connection') else conn.connection
                    cursor = dbapi_conn.cursor()
                    cursor.executescript(ddl_query)
                    return cursor.rowcount
                else:
                    result = conn.execute(text(ddl_query), params if params else {})
                    return result.rowcount
        except Exception as e:
            logger.error(f"Postgres execution failed on write statement: {e}")
            raise e
            
    def load_dataframe(self, df: pd.DataFrame, table_name: str, if_exists: str = "append"):
        """Inserts a full pandas DataFrame into a specific table."""
        try:
            with self.engine.begin() as conn:
                df.to_sql(table_name, conn, if_exists=if_exists, index=False)
            logger.info(f"Loaded DataFrame with {len(df)} rows into '{table_name}'.")
        except Exception as e:
            logger.error(f"Error loading DataFrame into table '{table_name}': {e}")
            raise e
            
    def health_check(self) -> bool:
        try:
            res = self.execute_query("SELECT 1")
            return not res.empty
        except Exception:
            return False
