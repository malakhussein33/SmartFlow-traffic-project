"""
Spark Batch Processing
======================
Reads historical Parquet events from HDFS/local, computes complex aggregates
(averages, peak hours, road rank, congestion stats), and loads reports to database.
"""
import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, sum, count, rank, desc, dense_rank
from pyspark.sql.window import Window
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.helpers import load_config
from utils.logger import get_logger

logger = get_logger("spark_batch")
load_dotenv()

class SparkBatchProcessor:
    def __init__(self, config_path: str = "./config/config.yaml"):
        self.config = load_config(config_path)
        self.s_cfg = self.config['spark']
        self.postgres_cfg = self.config['postgres']
        self.hdfs_cfg = self.config['hdfs']
        self.spark = self._create_spark_session()
        
    def _create_spark_session(self) -> SparkSession:
        logger.info("Initializing Spark Session for batch processing...")
        return SparkSession.builder \
            .appName(f"{self.s_cfg['app_name']}_Batch") \
            .master(self.s_cfg['master']) \
            .config("spark.jars.packages", "org.postgresql:postgresql:42.7.3") \
            .config("spark.executor.memory", self.s_cfg['executor_memory']) \
            .config("spark.driver.memory", self.s_cfg['driver_memory']) \
            .getOrCreate()
            
    def run_daily_reports(self):
        logger.info("Starting Daily Traffic Aggregations Batch Job...")
        
        # Load historical traffic path (fall back to local data directory if HDFS not running)
        hdfs_path = f"hdfs://{self.hdfs_cfg['namenode']}:{self.hdfs_cfg['port']}{self.hdfs_cfg['base_path']}/raw_traffic_stream"
        local_path = os.path.join(self.config['data']['processed_dir'], "raw_traffic_stream")
        
        # Check if local fallback is active or HDFS path exists
        # To avoid failure on local setup, we use local path fallback
        data_path = local_path if not os.path.exists("/hadoop/dfs") else hdfs_path
        
        if not os.path.exists(data_path) and not os.path.exists(local_path):
            # Try to read sample CSV instead to generate initial statistics
            logger.warning(f"Parquet source paths {data_path} not found. Reading from historical CSV as source.")
            csv_path = os.path.join(self.config['data']['sample_dir'], "historical_traffic.csv")
            if not os.path.exists(csv_path):
                logger.error("No historical traffic data source found. Batch aborted.")
                return
            df = self.spark.read.csv(csv_path, header=True, inferSchema=True)
        else:
            df = self.spark.read.parquet(data_path)
            
        logger.info(f"Loaded {df.count()} historical events for batch analysis.")
        
        # Calculate Aggregates per Road
        # columns: road_id, avg_speed, total_vehicles, peak_hour, congestion_hours, congestion_score
        # Calculate Peak Hour: Hour with max sum(vehicle_count)
        road_hour_traffic = df.groupBy("road_id", "hour").agg(sum("vehicle_count").alias("total_hour_vehicles"))
        windowSpec = Window.partitionBy("road_id").orderBy(desc("total_hour_vehicles"))
        peak_hour_df = road_hour_traffic.withColumn("rank", rank().over(windowSpec)) \
            .filter(col("rank") == 1) \
            .select("road_id", col("hour").alias("peak_hour"))

        # Calculate general road statistics
        road_stats = df.groupBy("road_id").agg(
            avg("average_speed_kmh").alias("avg_speed"),
            sum("vehicle_count").alias("total_vehicles"),
            avg("congestion_index").alias("congestion_score"),
            # Congestion hours count (congestion_index > 0.5)
            sum(when(col("congestion_index") > 0.5, 1).otherwise(0)).alias("congestion_hours")
        )
        
        # Merge stats and peak hour
        final_report_df = road_stats.join(peak_hour_df, "road_id") \
            .withColumn("report_type", col("road_id").cast("string")) \
            .withColumn("report_type", col("report_type").alias("DAILY")) \
            .withColumn("report_date", current_timestamp().cast("date"))
            
        # Select target schema columns
        # Table batch_reports: report_type, report_date, road_id, avg_speed, total_vehicles, peak_hour, congestion_hours, congestion_score
        report_payload = final_report_df.select(
            col("report_type"),
            col("report_date"),
            col("road_id"),
            col("avg_speed"),
            col("total_vehicles"),
            col("peak_hour"),
            col("congestion_hours"),
            col("congestion_score")
        )
        
        # Load reports into PostgreSQL
        logger.info("Writing computed reports into database batch_reports table...")
        pg_url = f"jdbc:postgresql://{self.postgres_cfg['host']}:{self.postgres_cfg['port']}/{self.postgres_cfg['db']}"
        properties = {
            "user": self.postgres_cfg['user'],
            "password": self.postgres_cfg['password'],
            "driver": "org.postgresql.Driver"
        }
        
        try:
            report_payload.write.jdbc(
                url=pg_url,
                table="batch_reports",
                mode="append",
                properties=properties
            )
            logger.info("Batch daily report completed and stored successfully.")
        except Exception as e:
            logger.error(f"Failed to load batch reports into Postgres: {e}")
            
    def stop(self):
        self.spark.stop()

if __name__ == '__main__':
    batch = SparkBatchProcessor()
    try:
        batch.run_daily_reports()
    finally:
        batch.stop()
