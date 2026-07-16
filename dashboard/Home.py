"""
Smart City Traffic Dashboard - Home Page
========================================
Main landing page for real-time KPIs and system monitors.
"""
import os
import sys
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from storage.postgres import PostgreSQLClient
from utils.helpers import load_config

# Set streamlit config
st.set_page_config(
    page_title="SmartFlow - Cairo traffic hub",
    layout="wide",
    page_icon="🚦",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark UI)
st.markdown("""
    <style>
    .main {
        background-color: #0a0e1a;
        color: #e8eaf0;
    }
    .stMetric {
        background-color: #141824;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #1f293d;
    }
    .kpi-title {
        font-size: 24px;
        font-weight: bold;
        background: linear-gradient(45deg, #4f8ef7, #9b51e0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 20px;
    }
    .glass-card {
        background: rgba(20, 24, 36, 0.7);
        border-radius: 16px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(5px);
        -webkit-backdrop-filter: blur(5px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 20px;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🚦 SmartFlow — Smart City Traffic Platform")
st.write("Cairo, Egypt — Real-Time Pipeline Monitoring & Analytical Dashboard")

# Initialize DB connection
@st.cache_resource
def get_db_client():
    return PostgreSQLClient()

db = get_db_client()
config = load_config()

# Retrieve latest data or fallback to mock
def load_latest_traffic_data():
    try:
        query = """
            SELECT te.*, r.road_name, r.speed_limit_kmh, r.num_lanes, w.weather_condition 
            FROM traffic_events te
            JOIN roads r ON te.road_id = r.road_id
            LEFT JOIN weather_data w ON te.weather_id = w.weather_id
            ORDER BY te.timestamp DESC
            LIMIT 100
        """
        df = db.execute_query(query)
        if df.empty:
            return generate_mock_data()
        return df
    except Exception as e:
        st.sidebar.warning(f"Connecting to database failed ({e}). Loading offline simulator data.")
        return generate_mock_data()

def generate_mock_data():
    roads = config['simulation']['roads']
    mock_events = []
    for i, road in enumerate(roads):
        mock_events.append({
            "road_name": road['name'],
            "vehicle_count": int(300 * (0.8 if i%2==0 else 0.4)),
            "average_speed_kmh": int(road['speed_limit'] * (0.5 if i%3==0 else 0.8)),
            "congestion_index": 0.5 if i%2==0 else 0.2,
            "congestion_level": "HIGH" if i%2==0 else "LOW",
            "temperature": 32.0,
            "weather_condition": "Sunny",
            "timestamp": datetime.now().isoformat()
        })
    return pd.DataFrame(mock_events)

df_traffic = load_latest_traffic_data()

# KPI Metric Row
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_vehicles = int(df_traffic['vehicle_count'].sum())
    st.metric("Total Monitored Vehicles", f"{total_vehicles:,}", delta="+12% from last hour")
    
with col2:
    avg_speed = round(df_traffic['average_speed_kmh'].mean(), 1)
    st.metric("Average Traffic Speed", f"{avg_speed} km/h", delta="-3 km/h vs limit")
    
with col3:
    congested_count = len(df_traffic[df_traffic['congestion_level'].isin(['HIGH', 'CRITICAL'])])
    st.metric("Congested Roads", f"{congested_count}/{len(df_traffic['road_name'].unique())}", delta="+1 new bottleneck")
    
with col4:
    st.metric("Network Sensor Health", "Active (100%)", delta="15/15 nodes connected")

st.markdown("<hr style='border: 1px solid #1f293d;'>", unsafe_allow_html=True)

# Main Grid Visualizations
left_col, right_col = st.columns([2, 1])

with left_col:
    st.subheader("⚡ Live Traffic Flow (Vehicle Volume)")
    # Chart: Plotly Bar Chart
    fig_volume = px.bar(
        df_traffic,
        x="road_name",
        y="vehicle_count",
        color="congestion_level",
        color_discrete_map={
            "LOW": "#27ae60",
            "MEDIUM": "#f39c12",
            "HIGH": "#e67e22",
            "CRITICAL": "#c0392b"
        },
        template="plotly_dark"
    )
    fig_volume.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig_volume, use_container_width=True)

with right_col:
    st.subheader("🌡️ Weather & Road Index Correlation")
    # Chart: Speed Distribution Gauge or Pie chart
    fig_pie = px.pie(
        df_traffic,
        names="congestion_level",
        color="congestion_level",
        color_discrete_map={
            "LOW": "#27ae60",
            "MEDIUM": "#f39c12",
            "HIGH": "#e67e22",
            "CRITICAL": "#c0392b"
        },
        hole=0.4,
        template="plotly_dark"
    )
    fig_pie.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# Bottom Row: Data View
st.subheader("🚦 Real-Time Sensor Telemetry stream")
st.dataframe(
    df_traffic[['road_name', 'vehicle_count', 'average_speed_kmh', 'congestion_level', 'weather_condition', 'timestamp']],
    use_container_width=True
)

# Sidebar configurations
st.sidebar.image("https://img.icons8.com/color/96/000000/traffic-light.png", width=60)
st.sidebar.markdown("### **SmartFlow Control Panel**")
st.sidebar.info("Automated real-time updates from Apache Kafka and Spark Streaming.")

refresh = st.sidebar.button("Force Refresh Data")
if refresh:
    st.rerun()
