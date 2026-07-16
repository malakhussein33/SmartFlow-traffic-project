# SmartFlow — Smart City Traffic Management & Ride Demand Prediction Platform

[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Kafka](https://img.shields.io/badge/Kafka-3.x-orange.svg)](https://kafka.apache.org/)
[![Spark](https://img.shields.io/badge/Spark-3.5-red.svg)](https://spark.apache.org/)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

SmartFlow is an end-to-end Big Data & Machine Learning platform for real-time Cairo city traffic telemetry ingestions, schema enrichment, historical storage in HDFS, aggregated batch reports, ML predictions, and visualization.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Simulators [Ingestion & Simulation]
        TS[Traffic Sensors Generator]
        WS[Weather API Simulator]
        HC[Historical CSV Seed]
    end

    subgraph StreamingBroker [Message Broker]
        K[Apache Kafka]
        KUI[Kafka UI Monitor]
        K --> KUI
    end

    subgraph RealTimeProcessing [Processing Layer]
        SS[Spark Structured Streaming]
    end

    subgraph DataWarehouse [Data Storage Layer]
        HDFS[(Hadoop HDFS - Parquet)]
        PG[(PostgreSQL Database)]
    end

    subgraph OfflineBatch [Analytics & ML]
        BP[Spark Batch Jobs]
        ML[XGBoost & RF Models]
    end

    subgraph DashboardApp [User Interface]
        ST[Streamlit Dashboard]
    end

    TS & WS --> K
    K --> SS
    SS -->|Write Raw events| HDFS
    SS -->|Write Transformed| PG
    HC -->|Direct Seed| PG
    HDFS & PG --> BP
    BP --> ML
    PG & ML --> ST
```

---

## 🗺️ Entity Relationship (ER) Diagram

```mermaid
erDiagram
    roads {
        int road_id PK
        varchar road_name UK
        varchar road_type
        float length_km
        int num_lanes
        int speed_limit_kmh
        varchar city
        timestamp created_at
    }
    sensor_locations {
        varchar sensor_id PK
        int road_id FK
        float latitude
        float longitude
        date installation_date
        boolean is_active
        timestamp created_at
    }
    weather_data {
        int weather_id PK
        timestamptz timestamp
        float temperature_celsius
        float humidity_percent
        float rain_mm
        float wind_speed_kmh
        varchar weather_condition
        varchar city
        timestamp created_at
    }
    traffic_events {
        int event_id PK
        varchar sensor_id FK
        int road_id FK
        timestamptz timestamp
        int vehicle_count
        float average_speed_kmh
        float traffic_density
        float congestion_index
        varchar congestion_level
        int weather_id FK
        int hour
        int day_of_week
        int month
        boolean is_weekend
        boolean is_rush_hour
        timestamp created_at
    }
    ride_requests {
        int request_id PK
        timestamptz timestamp
        float pickup_latitude
        float pickup_longitude
        float dropoff_latitude
        float dropoff_longitude
        int pickup_road_id FK
        float distance_km
        float duration_minutes
        float fare_amount
        varchar status
        timestamp created_at
    }
    predictions {
        int prediction_id PK
        varchar model_name
        varchar prediction_type
        int road_id FK
        varchar sensor_id FK
        timestamptz predicted_at
        int prediction_horizon_minutes
        int predicted_vehicle_count
        varchar predicted_congestion_level
        float predicted_avg_speed
        float confidence_score
        int actual_vehicle_count
        varchar actual_congestion_level
        float rmse
        timestamp created_at
    }
    batch_reports {
        int report_id PK
        varchar report_type
        date report_date
        int road_id FK
        float avg_speed
        bigint total_vehicles
        int peak_hour
        int congestion_hours
        float congestion_score
        timestamp created_at
    }

    roads ||--o{ sensor_locations : "monitors"
    roads ||--o{ traffic_events : "contains"
    roads ||--o{ ride_requests : "starts_at"
    roads ||--o{ predictions : "applies_to"
    roads ||--o{ batch_reports : "summarizes"
    sensor_locations ||--o{ traffic_events : "logs"
    sensor_locations ||--o{ predictions : "locates"
    weather_data ||--o{ traffic_events : "affects"
```

---

## 🚀 Installation & Local Operations

### Prerequisites
*   Python 3.11 (Standard Windows distribution recommended)
*   Docker & Docker Compose (Optional; if absent, the app falls back to local SQLite)
*   Java JDK 11 (For running Spark streaming jobs locally)

---

### Step 1: Locate standard Python on Windows
If standard Python is installed, locate its absolute path using one of the following commands:
```powershell
# Option A: Query the system search path for python
where.exe python

# Option B: Search for installed python versions in your user AppData directory
Resolve-Path "C:\Users\*\AppData\Local\Programs\Python\Python*\python.exe"
```
*Take note of the printed path (e.g. `C:\Users\PC\AppData\Local\Programs\Python\Python311\python.exe`).*

---

### Step 2: Create a Virtual Environment (`venv`)
Use the located python executable path (or just `python` if standard python is in your PATH) to create the environment:
```powershell
# Create a venv named 'venv'
C:\Users\<Your_User>\AppData\Local\Programs\Python\Python311\python.exe -m venv venv
```

---

### Step 3: Activate the Virtual Environment (Optional)
If you want to activate the virtual environment in your current terminal session:
```powershell
# PowerShell
.\venv\Scripts\Activate.ps1

# CMD
.\venv\Scripts\activate.bat
```

---

### Step 4: Install Dependencies
Run pip using the virtual environment's pip executable directly:
```powershell
# Install required packages
.\venv\Scripts\pip.exe install -r requirements.txt
.\venv\Scripts\pip.exe install psycopg2-binary

# Copy environment template
cp .env.example .env
```

---

### Step 5: Spin up database and Kafka (Optional)
If Docker Desktop is installed and you want to use the live Kafka/Postgres streaming pipeline:
```bash
docker-compose up -d postgres zookeeper kafka kafka-ui
```
*Note: If you do not have Docker running, you can skip this step. The database client automatically falls back to a local SQLite database (`data/sample/local_smartflow.db`) populated directly from the generated CSV files.*

---

### Step 6: Generate Data, Ingest Schema, & Train Models (Direct venv Commands)
Run these commands using the virtual environment's python directly:
```powershell
# 1. Generate 30 days of mock historical CSVs
.\venv\Scripts\python simulator/historical_generator.py

# 2. Bootstrap database schema and seed/ingest data (Creates SQLite DB locally or loads PostgreSQL)
.\venv\Scripts\python ingestion/ingestion.py

# 3. Train initial ML Models on the generated dataset
.\venv\Scripts\python ml/train.py
```

---

### Step 7: Start the Streamlit Dashboard UI
Launch the dashboard using the virtual environment's streamlit executable directly:
```powershell
.\venv\Scripts\streamlit run dashboard/Home.py
```
Open **`http://localhost:8501`** in your browser. If database containers were skipped, the app will run seamlessly in offline SQLite fallback mode!

---

## 🛠️ Makefile targets
Simplify developer commands:
*   `make setup`: Installs packages.
*   `make generate-data`: Generates mock historical CSVs.
*   `make start-simulator`: Starts real-time traffic generators.
*   `make train-models`: Trains scikit-learn & XGBoost estimators.
*   `make test`: Runs test suite.
