"""
About Page
==========
System documentation, pipelines, architecture overview, and contributors.
"""
import streamlit as st

st.set_page_config(page_title="About | SmartFlow", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0a0e1a; color: #e8eaf0; }
    </style>
""", unsafe_allow_html=True)

st.title("ℹ️ About the SmartFlow Platform")
st.write("University Graduation Project — Big Data & Machine Learning Framework.")

st.subheader("💡 Key Objectives")
st.write("""
This platform simulates real smart city data pipelines. Using Python, Kafka, Spark Streaming, HDFS, PostgreSQL, and Streamlit, 
it ingests live IoT sensors telemetry streams, structures records dynamically inside our relational data warehouse, and partition logs in HDFS.
""")

st.subheader("🏗️ System Architecture Flow")
st.markdown("""
```
[Traffic Sensors / Simulators] ---> [Apache Kafka Topics]
                                           |
                                           v
                                   [Spark Streaming]
                                     (ETL & Window)
                                           |
                   +-----------------------+-----------------------+
                   |                                               |
                   v                                               v
      [PostgreSQL Data Warehouse]                      [HDFS Historical Files]
        (Active Stream Analytics)                       (Parquet Partitioning)
                   |                                               |
                   v                                               v
        [Streamlit Dashboard]                             [Spark Batch Jobs]
     (AI Forecasts & KPI Maps)                             (Daily aggregates)
                                                                   |
                                                                   v
                                                          [Machine Learning]
                                                        (Random Forest/XGBoost)
```
""")

st.subheader("🛠️ Technology Stack Breakdown")
st.markdown("""
*   **Ingestion & Simulator:** Python (Faker, Kafka-python-ng)
*   **Message Broker:** Apache Kafka & Zookeeper
*   **Real-time Processing:** Apache Spark (Structured Streaming)
*   **Relational Storage:** PostgreSQL
*   **Historical Data Warehouse:** Apache Hadoop (HDFS) partitioned as Parquet files
*   **AI Predictor:** Scikit-learn, XGBoost, and StandardScaler transforms
*   **Interactive Visualizations:** Streamlit, Folium, Plotly Express
""")
