"""
Traffic Predictions Page
========================
Uses trained machine learning models to forecast vehicle demands and congestion.
"""
import os
import sys
import streamlit as st
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from ml.predict import TrafficPredictor
from utils.helpers import load_config

st.set_page_config(page_title="AI Predictions | SmartFlow", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0a0e1a; color: #e8eaf0; }
    .pred-card {
        background-color: #141824;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #1f293d;
        text-align: center;
    }
    .pred-val {
        font-size: 36px;
        font-weight: bold;
        color: #4f8ef7;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🔮 AI Traffic & Demand Predictions")
st.write("Leverage Random Forest & XGBoost algorithms to predict congestion metrics.")

# Load predictor
@st.cache_resource
def get_predictor():
    return TrafficPredictor()

predictor = get_predictor()
config = load_config()

# Setup simulation inputs
col_input, col_pred = st.columns([1, 2])

with col_input:
    st.subheader("Simulated Prediction Input Features")
    
    road_selected = st.selectbox(
        "Select Road segment",
        options=[r['name'] for r in config['simulation']['roads']]
    )
    
    # Extract road features
    road_meta = next(r for r in config['simulation']['roads'] if r['name'] == road_selected)
    
    hour_val = st.slider("Hour of Day", 0, 23, 12)
    day_selected = st.selectbox("Day of Week", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
    day_mapping = {
        "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
        "Friday": 4, "Saturday": 5, "Sunday": 6
    }
    day_of_week = day_mapping[day_selected]
    
    month_val = st.slider("Month", 1, 12, 6)
    temp_val = st.number_input("Temperature (°C)", value=32.0, min_value=0.0, max_value=50.0)
    humidity_val = st.number_input("Humidity (%)", value=50.0, min_value=0.0, max_value=100.0)
    speed_val = st.slider("Current Avg Speed (km/h)", 5, road_meta['speed_limit'], int(road_meta['speed_limit'] * 0.8))
    
    is_wknd = day_of_week in [4, 5]
    is_rush = hour_val in [7, 8, 9, 17, 18, 19]
    
    # Prepare feature dict
    feat_dict = {
        "hour": hour_val,
        "day_of_week": day_of_week,
        "month": month_val,
        "is_weekend": is_wknd,
        "is_rush_hour": is_rush,
        "temperature_celsius": temp_val,
        "humidity_percent": humidity_val,
        "average_speed_kmh": float(speed_val),
        "num_lanes": road_meta['lanes'],
        "speed_limit_kmh": road_meta['speed_limit']
    }

with col_pred:
    st.subheader("Model Outputs & Congestion Indexes")
    
    # Run prediction
    result = predictor.predict_congestion(feat_dict)
    
    # KPI Display Cards
    card1, card2 = st.columns(2)
    with card1:
        st.markdown(
            f"""<div class='pred-card'>
                <h4>Predicted Vehicle Volume</h4>
                <div class='pred-val'>{result['predicted_vehicle_count']}</div>
                <p>Vehicles per kilometer</p>
            </div>""",
            unsafe_allow_html=True
        )
    with card2:
        congestion_color = {
            "LOW": "#27ae60",
            "MEDIUM": "#f39c12",
            "HIGH": "#e67e22",
            "CRITICAL": "#c0392b"
        }.get(result['predicted_congestion_level'], "#4f8ef7")
        
        st.markdown(
            f"""<div class='pred-card'>
                <h4>Predicted Congestion Level</h4>
                <div class='pred-val' style='color:{congestion_color};'>{result['predicted_congestion_level']}</div>
                <p>Congestion Index: {result['predicted_congestion_index']}</p>
            </div>""",
            unsafe_allow_html=True
        )
        
    st.markdown("---")
    st.subheader("24-Hour Congestion Forecast")
    
    # Generate 24-hour predictions list
    predictions_24h = []
    for h in range(24):
        hourly_feat = feat_dict.copy()
        hourly_feat['hour'] = h
        hourly_feat['is_rush_hour'] = h in [7, 8, 9, 17, 18, 19]
        
        pred_val = predictor.predict_vehicle_count(hourly_feat)
        predictions_24h.append({
            "Hour": f"{h:02d}:00",
            "Predicted Vehicles": int(pred_val)
        })
        
    df_forecast = pd.DataFrame(predictions_24h)
    st.line_chart(df_forecast.set_index("Hour"))
