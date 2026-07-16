"""
Live Traffic Map
================
Visualizes sensor coordinate locations on a Folium map with color-coded congestion markers.
"""
import os
import sys
import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from storage.postgres import PostgreSQLClient
from utils.helpers import load_config

st.set_page_config(page_title="Live Map | SmartFlow", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0a0e1a; color: #e8eaf0; }
    </style>
""", unsafe_allow_html=True)

st.title("🗺️ Live Traffic Map & Coordinates Explorer")
st.write("Real-time locations of Cairo traffic sensors and congestion nodes.")

# Init DB client
@st.cache_resource
def get_db_client():
    return PostgreSQLClient()

db = get_db_client()
config = load_config()

def load_locations_with_congestion():
    try:
        # Pull current traffic status using DB view if database is active
        query = "SELECT * FROM v_current_traffic_status"
        df = db.execute_query(query)
        if df.empty:
            return generate_mock_locations()
        return df
    except Exception:
        return generate_mock_locations()

def generate_mock_locations():
    # Load coordinates from configuration roads list
    roads = config['simulation']['roads']
    mock_locs = []
    for i, road in enumerate(roads):
        mock_locs.append({
            "sensor_id": f"SENSOR_{road['name'].replace(' ', '_').upper()}_01",
            "road_name": road['name'],
            "latitude": road['lat'],
            "longitude": road['lon'],
            "vehicle_count": int(150 + 200 * (i % 2)),
            "average_speed_kmh": int(road['speed_limit'] * (0.4 if i % 2 == 0 else 0.9)),
            "congestion_index": 0.6 if i % 2 == 0 else 0.1,
            "congestion_level": "HIGH" if i % 2 == 0 else "LOW",
            "temperature_celsius": 32.5,
            "weather_condition": "Sunny",
            "timestamp": datetime.now().isoformat()
        })
    return pd.DataFrame(mock_locs)

df_locs = load_locations_with_congestion()

# Setup layout
col_map, col_details = st.columns([3, 1])

# Determine marker color based on congestion
def get_marker_color(level: str) -> str:
    color_map = {
        "LOW": "green",
        "MEDIUM": "orange",
        "HIGH": "red",
        "CRITICAL": "darkred"
    }
    return color_map.get(level, "blue")

with col_map:
    # Centered on Cairo
    cairo_center = [30.0444, 31.2357]
    m = folium.Map(location=cairo_center, zoom_start=11, tiles="Cartodb dark_matter")
    
    # Add coordinates markers
    for _, row in df_locs.iterrows():
        color = get_marker_color(row['congestion_level'])
        popup_html = f"""
            <div style="font-family: Arial, sans-serif; font-size: 12px; color: #333;">
                <b>Sensor:</b> {row['sensor_id']}<br>
                <b>Road:</b> {row['road_name']}<br>
                <b>Vehicles:</b> {row['vehicle_count']}<br>
                <b>Avg Speed:</b> {row['average_speed_kmh']} km/h<br>
                <b>Congestion:</b> {row['congestion_level']}<br>
                <b>Condition:</b> {row['weather_condition']} ({row.get('temperature_celsius', 32.0)}°C)
            </div>
        """
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=12,
            popup=folium.Popup(popup_html, max_width=250),
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6
        ).add_to(m)
        
    folium_static(m, width=950, height=550)

with col_details:
    st.subheader("⚠️ Critical Nodes")
    critical_df = df_locs[df_locs['congestion_level'].isin(['HIGH', 'CRITICAL'])]
    if critical_df.empty:
        st.success("All roads are flowing smoothly! No high congestion indices recorded.")
    else:
        for _, row in critical_df.iterrows():
            st.error(f"**{row['road_name']}**\n- Speed: {row['average_speed_kmh']} km/h\n- Congestion Level: {row['congestion_level']}")
            
    st.write("---")
    st.subheader("Filter Sensoring Nodes")
    levels = df_locs['congestion_level'].unique()
    selected_levels = st.multiselect("Select Congestion Levels", options=levels, default=levels)
    filtered_df = df_locs[df_locs['congestion_level'].isin(selected_levels)]
    st.write(f"Showing {len(filtered_df)} active points on map.")
