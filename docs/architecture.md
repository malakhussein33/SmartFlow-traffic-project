# SmartCity Traffic Platform Architecture Deep Dive

Here is the flow chart representation of our real-time pipelines.

## Data flow
```mermaid
sequenceDiagram
    participant Simulator as Traffic/Weather Simulators
    participant Kafka as Apache Kafka Broker
    participant SparkStream as Spark Structured Streaming
    participant Postgres as PostgreSQL Database
    participant HDFS as Hadoop Distributed File System (Parquet)
    participant SparkBatch as Spark Batch Analytics
    participant ML as ML model (Random Forest / XGBoost)

    Simulator->>Kafka: Publish JSON records
    Kafka->>SparkStream: Poll event batches
    SparkStream->>SparkStream: Schema Validation & Transforms
    SparkStream->>Postgres: ForeachBatch JDBC Append
    SparkStream->>HDFS: Parquet write partitioned by month/hour
    HDFS->>SparkBatch: Hourly/Daily read jobs
    SparkBatch->>SparkBatch: Multi-source join with weather
    SparkBatch->>Postgres: Load batch aggregates
    SparkBatch->>ML: Retrain features estimator
```

This sequence represents the flow from edge sensors simulated in Cairo all the way to analytical dashboards.
