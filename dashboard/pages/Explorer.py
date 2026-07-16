"""
Data Explorer Page
==================
Enables users to search, filter, and export datasets.
"""
import os
import sys
import streamlit as st
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from storage.postgres import PostgreSQLClient
from utils.helpers import load_config

st.set_page_config(page_title="Data Explorer | SmartFlow", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0a0e1a; color: #e8eaf0; }
    </style>
""", unsafe_allow_html=True)

st.title("🔍 Data Explorer & Table Exporter")
st.write("Browse and export raw datasets from database tables.")

@st.cache_resource
def get_db_client():
    return PostgreSQLClient()

db = get_db_client()
config = load_config()

# Select dataset to search
dataset_choice = st.selectbox(
    "Select Table to Explore",
    ["roads", "sensor_locations", "weather_data", "traffic_events", "ride_requests", "predictions", "batch_reports"]
)

def fetch_table(table_name: str) -> pd.DataFrame:
    try:
        query = f"SELECT * FROM {table_name} LIMIT 1000"
        df = db.execute_query(query)
        if df.empty:
            return generate_fallback_explorer_data(table_name)
        return df
    except Exception:
        return generate_fallback_explorer_data(table_name)

def generate_fallback_explorer_data(table_name: str) -> pd.DataFrame:
    # Basic skeleton fallback for development environments
    if table_name == "roads":
        roads = config['simulation']['roads']
        return pd.DataFrame([{"road_id": i, "road_name": r['name'], "speed_limit_kmh": r['speed_limit'], "num_lanes": r['lanes']} for i, r in enumerate(roads, 1)])
    elif table_name == "sensor_locations":
        roads = config['simulation']['roads']
        return pd.DataFrame([{"sensor_id": f"SENSOR_{r['name'].replace(' ', '_').upper()}_01", "latitude": r['lat'], "longitude": r['lon']} for r in roads])
    else:
        # Generic mock
        return pd.DataFrame([{"timestamp": datetime.now().isoformat(), "info": "Demo fallback. Populate database with simulator."}])

df_explorer = fetch_table(dataset_choice)

# Add search filtering
search_term = st.text_input("Global Search (regex / substring filter)", "")
if search_term:
    # Filter columns that contain search term
    mask = df_explorer.astype(str).apply(lambda x: x.str.contains(search_term, case=False)).any(axis=1)
    df_filtered = df_explorer[mask]
else:
    df_filtered = df_explorer

st.write(f"Showing {len(df_filtered)} records.")
st.dataframe(df_filtered, use_container_width=True)

# Export option
csv_data = df_filtered.to_csv(index=False).encode('utf-8')
st.download_button(
    label=f"📥 Download {dataset_choice} as CSV",
    data=csv_data,
    file_name=f"smartcity_{dataset_choice}.csv",
    mime="text/csv"
)
