"""
Spark Structured Streaming App
==============================
Consumes traffic events stream from Kafka, processes/enriches them with window metrics,
and writes to HDFS (raw) and PostgreSQL (processed).
"""
import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, when, hour, dayofweek, month, to_timestamp, window, avg, sum, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, BooleanType, TimestampType
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.helpers import load_config
from utils.logger import get_logger

logger = get_logger("spark_streaming")
load_dotenv()

class SparkStreamingProcessor:
    def __init__(self, config_path: str = "./config/config.yaml"):
        self.config = load_config(config_path)
        self.s_cfg = self.config['spark']
        self.k_cfg = self.config['kafka']
        self.postgres_cfg = self.config['postgres']
        self.spark = self._create_spark_session()
        
    def _create_spark_session(self) -> SparkSession:
        logger.info("Initializing Spark Session with Kafka packages...")
        # Add required dependencies for kafka streaming and postgres jdbc
        return SparkSession.builder \
            .appName(self.s_cfg['app_name']) \
            .master(self.s_cfg['master']) \
            .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,org.postgresql:postgresql:42.7.3") \
            .config("spark.executor.memory", self.s_cfg['executor_memory']) \
            .config("spark.driver.memory", self.s_cfg['driver_memory']) \
            .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true") \
            .getOrCreate()
            
    def _get_traffic_schema(self) -> StructType:
        return StructType([
            StructField("sensor_id", StringType(), True),
            StructField("road_name", StringType(), True),
            StructField("latitude", DoubleType(), True),
            StructField("longitude", DoubleType(), True),
            StructField("vehicle_count", IntegerType(), True),
            StructField("average_speed_kmh", DoubleType(), True),
            StructField("traffic_density", DoubleType(), True),
            StructField("congestion_index", DoubleType(), True),
            StructField("congestion_level", StringType(), True),
            StructField("weather_condition", StringType(), True),
            StructField("temperature", DoubleType(), True),
            StructField("humidity", DoubleType(), True),
            StructField("rain_mm", DoubleType(), True),
            StructField("wind_speed_kmh", DoubleType(), True),
            StructField("timestamp", StringType(), True),
            StructField("hour", IntegerType(), True),
            StructField("day_of_week", IntegerType(), True),
            StructField("month", IntegerType(), True),
            StructField("is_weekend", BooleanType(), True),
            StructField("is_rush_hour", BooleanType(), True)
        ])

    def write_to_postgres(self, batch_df, batch_id):
        """ForeachBatch sink to write parsed streams to PostgreSQL database."""
        logger.info(f"Writing streaming micro-batch {batch_id} to PostgreSQL...")
        
        # Postgres URL setup
        pg_url = f"jdbc:postgresql://{self.postgres_cfg['host']}:{self.postgres_cfg['port']}/{self.postgres_cfg['db']}"
        properties = {
            "user": self.postgres_cfg['user'],
            "password": self.postgres_cfg['password'],
            "driver": "org.postgresql.Driver"
        }
        
        try:
            # Drop unnecessary transient columns before writing to postgres if schema doesn't fit
            cleaned_batch = batch_df.drop("timestamp_parsed")
            cleaned_batch.write.jdbc(
                url=pg_url,
                table="traffic_events",
                mode="append",
                properties=properties
            )
            logger.info(f"Micro-batch {batch_id} successfully saved to Postgres.")
        except Exception as e:
            logger.error(f"Failed to write micro-batch {batch_id} to Postgres: {e}")

    def run_pipeline(self):
        logger.info("Setting up Spark streaming read from Kafka...")
        
        # Connect to Kafka traffic stream topic
        kafka_stream_df = self.spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", self.k_cfg['bootstrap_servers']) \
            .option("subscribe", self.k_cfg['topics']['traffic']) \
            .option("startingOffsets", "latest") \
            .load()

        # Deserialize string value column
        raw_stream_df = kafka_stream_df.selectExpr("CAST(value AS STRING) as json_value")
        
        # Parse schema
        parsed_df = raw_stream_df.select(
            from_json(col("json_value"), self._get_traffic_schema()).alias("data")
        ).select("data.*")
        
        # Parse text timestamp column as spark timestamp
        enriched_df = parsed_df.withColumn("timestamp_parsed", to_timestamp(col("timestamp")))
        
        # Clean invalid rows (zero speed or negative vehicles)
        cleaned_df = enriched_df.filter(
            (col("vehicle_count") >= 0) & 
            (col("average_speed_kmh") >= 0) & 
            (col("latitude").between(-90.0, 90.0)) & 
            (col("longitude").between(-180.0, 180.0))
        )
        
        # Spark Streaming aggregation using 10 minutes watermarking and sliding window
        windowed_metrics_df = cleaned_df \
            .withWatermark("timestamp_parsed", "10 minutes") \
            .groupBy(
                window(col("timestamp_parsed"), "5 minutes", "1 minute"),
                col("road_name")
            ).agg(
                avg("vehicle_count").alias("avg_vehicle_count"),
                avg("average_speed_kmh").alias("avg_speed_kmh"),
                avg("congestion_index").alias("avg_congestion_index")
            )

        # 1. Write structured raw events to local directory / HDFS (as Parquet)
        checkpoint_raw = os.path.join(self.s_cfg['checkpoint_dir'], "raw_traffic")
        raw_hdfs_path = f"{self.config['hdfs']['base_path']}/raw_traffic_stream"
        
        raw_query = cleaned_df.writeStream \
            .format("parquet") \
            .option("path", raw_hdfs_path) \
            .option("checkpointLocation", checkpoint_raw) \
            .partitionBy("month", "hour") \
            .outputMode("append") \
            .start()

        # 2. Write enriched traffic events to PostgreSQL using foreachBatch
        checkpoint_pg = os.path.join(self.s_cfg['checkpoint_dir'], "postgres_traffic")
        
        pg_query = cleaned_df.writeStream \
            .foreachBatch(self.write_to_postgres) \
            .option("checkpointLocation", checkpoint_pg) \
            .outputMode("append") \
            .start()
            
        logger.info("Spark Structured Streaming queries started.")
        
        # Wait for termination
        raw_query.awaitTermination()
        pg_query.awaitTermination()

if __name__ == '__main__':
    streaming_app = SparkStreamingProcessor()
    streaming_app.run_pipeline()
