"""
Historical Analytics Page
==========================
Displays trends, peak hours, heatmaps, and summaries using Plotly.
"""
import os
import sys
import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from storage.postgres import PostgreSQLClient
from utils.helpers import load_config

st.set_page_config(page_title="Historical Analytics | SmartFlow", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0a0e1a; color: #e8eaf0; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Historical Traffic Analytics")
st.write("Aggregated trend reports from Cairo traffic historical database.")

@st.cache_resource
def get_db_client():
    return PostgreSQLClient()

db = get_db_client()
config = load_config()

def load_historical_data():
    try:
        # Load historical traffic from database if available
        query = """
            SELECT te.timestamp, te.vehicle_count, te.average_speed_kmh, te.congestion_index, te.hour, te.day_of_week, r.road_name 
            FROM traffic_events te
            JOIN roads r ON te.road_id = r.road_id
            ORDER BY te.timestamp ASC
            LIMIT 5000
        """
        df = db.execute_query(query)
        if df.empty:
            return generate_mock_historical()
        return df
    except Exception:
        return generate_mock_historical()

def generate_mock_historical():
    roads = [r['name'] for r in config['simulation']['roads']]
    data = []
    base_time = datetime.now() - timedelta(days=7)
    
    for day in range(7):
        for hr in range(24):
            for road in roads[:5]: # limit to first 5 roads for chart performance
                is_rush = hr in [7, 8, 9, 17, 18, 19]
                v_count = int(120 + 250 * (1.2 if is_rush else 0.4))
                avg_speed = int(60 * (0.5 if is_rush else 0.9))
                
                data.append({
                    "timestamp": base_time + timedelta(days=day, hours=hr),
                    "vehicle_count": v_count,
                    "average_speed_kmh": avg_speed,
                    "congestion_index": 0.7 if is_rush else 0.1,
                    "hour": hr,
                    "day_of_week": (base_time + timedelta(days=day)).weekday(),
                    "road_name": road
                })
    return pd.DataFrame(data)

df_hist = load_historical_data()

# Tabs for separate reports
tab_trends, tab_peak, tab_heatmap = st.tabs(["📈 Traffic Volumes", "⏰ Peak Hours Analysis", "🔥 Congestion Heatmap"])

with tab_trends:
    st.subheader("Daily Vehicle Count Trends")
    # Multiselect for roads
    selected_roads = st.multiselect("Select Roads to Analyze", options=df_hist['road_name'].unique(), default=df_hist['road_name'].unique()[:3])
    
    filtered_df = df_hist[df_hist['road_name'].isin(selected_roads)]
    
    if filtered_df.empty:
        st.warning("Please select at least one road.")
    else:
        # Group by road and timestamp (downsampled by hour or day depending on data size)
        # For simplicity, we plot vehicle count directly
        fig_trend = px.line(
            filtered_df,
            x="timestamp",
            y="vehicle_count",
            color="road_name",
            template="plotly_dark",
            title="Hourly Volume Trends"
        )
        fig_trend.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_trend, use_container_width=True)

with tab_peak:
    st.subheader("Traffic Distribution by Hour of Day")
    # Average traffic hourly
    hourly_df = df_hist.groupby(["hour", "road_name"])["vehicle_count"].mean().reset_index()
    
    fig_hourly = px.bar(
        hourly_df,
        x="hour",
        y="vehicle_count",
        color="road_name",
        template="plotly_dark",
        barmode="group",
        title="Average Vehicle Volumes by Hour"
    )
    fig_hourly.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_hourly, use_container_width=True)

with tab_heatmap:
    st.subheader("Congestion Heatmap Matrix")
    # Pivot to Hour vs Road
    heatmap_data = df_hist.pivot_table(
        index="road_name",
        columns="hour",
        values="congestion_index",
        aggfunc="mean"
    )
    
    fig_heatmap = px.imshow(
        heatmap_data,
        labels=dict(x="Hour of Day", y="Road Name", color="Avg Congestion Index"),
        color_continuous_scale="RdYlGn_r",
        template="plotly_dark"
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)
