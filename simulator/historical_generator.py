"""
Historical Data Generator
=========================
Generates 90 days of synthetic historical traffic events, weather data, and ride requests.
Saves outputs to the configured sample data directory as CSV files.
"""
import os
import sys
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.helpers import load_config, calculate_traffic_density, calculate_congestion_index, get_congestion_level, is_rush_hour, is_weekend
from utils.logger import get_logger

logger = get_logger("historical_generator")
load_dotenv()

class HistoricalDataGenerator:
    def __init__(self, config_path: str = "./config/config.yaml"):
        self.config = load_config(config_path)
        self.roads = self.config['simulation']['roads']
        self.output_dir = self.config['data']['sample_dir']
        os.makedirs(self.output_dir, exist_ok=True)
        
    def generate_all_data(self, days: int = 90):
        logger.info(f"Generating {days} days of historical city data...")
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)
        
        # 1. Generate Weather
        weather_list = []
        current_time = start_time
        weather_id = 1
        while current_time <= end_time:
            # Cairo weather simulation
            month = current_time.month
            hour = current_time.hour
            
            if month in [6, 7, 8]:
                base_temp = 34.0
            elif month in [12, 1, 2]:
                base_temp = 15.0
            else:
                base_temp = 25.0
                
            if 12 <= hour <= 16:
                temp = base_temp + random.uniform(4.0, 8.0)
            elif 2 <= hour <= 5:
                temp = base_temp - random.uniform(4.0, 8.0)
            else:
                temp = base_temp + random.uniform(-2.0, 2.0)
                
            humidity = random.uniform(35.0, 80.0)
            rain = 0.0 if random.random() > 0.02 else random.uniform(0.5, 8.0)
            wind = random.uniform(5.0, 30.0)
            condition = "Sunny"
            if rain > 0:
                condition = "Rainy" if rain > 3.0 else "Drizzle"
                
            weather_list.append({
                "weather_id": weather_id,
                "timestamp": current_time.isoformat(),
                "temperature_celsius": round(temp, 1),
                "humidity_percent": round(humidity, 1),
                "rain_mm": round(rain, 2),
                "wind_speed_kmh": round(wind, 2),
                "weather_condition": condition,
                "city": "Cairo"
            })
            weather_id += 1
            current_time += timedelta(hours=1)
            
        weather_df = pd.DataFrame(weather_list)
        weather_df.to_csv(os.path.join(self.output_dir, "historical_weather.csv"), index=False)
        logger.info(f"Saved {len(weather_df)} weather records.")
        
        # 2. Generate Roads Table
        roads_list = []
        for i, road in enumerate(self.roads, 1):
            roads_list.append({
                "road_id": i,
                "road_name": road["name"],
                "road_type": "Urban" if road["speed_limit"] <= 60 else "Highway",
                "length_km": round(random.uniform(2.0, 15.0), 1) if road["speed_limit"] <= 60 else round(random.uniform(15.0, 100.0), 1),
                "num_lanes": road["lanes"],
                "speed_limit_kmh": road["speed_limit"],
                "city": "Cairo"
            })
        roads_df = pd.DataFrame(roads_list)
        roads_df.to_csv(os.path.join(self.output_dir, "historical_roads.csv"), index=False)
        logger.info(f"Saved {len(roads_df)} road records.")
        
        # 3. Generate Sensors Table
        sensors_list = []
        for road in roads_list:
            sensors_list.append({
                "sensor_id": f"SENSOR_{road['road_name'].replace(' ', '_').upper()}_01",
                "road_id": road["road_id"],
                "latitude": self.roads[road["road_id"]-1]["lat"],
                "longitude": self.roads[road["road_id"]-1]["lon"],
                "installation_date": (start_time - timedelta(days=100)).date().isoformat(),
                "is_active": True
            })
        sensors_df = pd.DataFrame(sensors_list)
        sensors_df.to_csv(os.path.join(self.output_dir, "historical_sensors.csv"), index=False)
        logger.info(f"Saved {len(sensors_df)} sensor records.")

        # 4. Generate Traffic Events
        # Generates events every hour for each sensor to keep file size reasonable
        traffic_list = []
        current_time = start_time
        
        while current_time <= end_time:
            hour = current_time.hour
            day_of_week = current_time.weekday()
            month = current_time.month
            
            rush = is_rush_hour(hour)
            weekend = is_weekend(day_of_week)
            
            # Find closest weather record
            # We match using index calculation for fast execution
            hours_diff = int((current_time - start_time).total_seconds() / 3600)
            matched_w_id = weather_list[min(hours_diff, len(weather_list)-1)]["weather_id"]
            
            for road in roads_list:
                sensor_id = f"SENSOR_{road['road_name'].replace(' ', '_').upper()}_01"
                base_capacity = road['num_lanes'] * 150
                
                if rush:
                    vehicle_factor = random.uniform(0.7, 1.2)
                elif weekend:
                    vehicle_factor = random.uniform(0.2, 0.5)
                else:
                    vehicle_factor = random.uniform(0.4, 0.8)
                    
                if 23 <= hour or hour <= 5:
                    vehicle_factor = random.uniform(0.05, 0.2)
                    
                vehicle_count = int(base_capacity * vehicle_factor)
                speed_factor = 1.0 - (vehicle_count / (base_capacity * 1.5))
                speed_factor = max(0.1, min(1.1, speed_factor))
                
                avg_speed = road['speed_limit_kmh'] * speed_factor + random.uniform(-5.0, 5.0)
                avg_speed = max(5.0, min(road['speed_limit_kmh'] * 1.2, avg_speed))
                
                density = calculate_traffic_density(vehicle_count, road['length_km'], road['num_lanes'])
                congestion_index = calculate_congestion_index(avg_speed, road['speed_limit_kmh'])
                congestion_level = get_congestion_level(congestion_index)
                
                traffic_list.append({
                    "sensor_id": sensor_id,
                    "road_id": road["road_id"],
                    "timestamp": current_time.isoformat(),
                    "vehicle_count": vehicle_count,
                    "average_speed_kmh": round(avg_speed, 2),
                    "traffic_density": round(density, 2),
                    "congestion_index": round(congestion_index, 2),
                    "congestion_level": congestion_level,
                    "weather_id": matched_w_id,
                    "hour": hour,
                    "day_of_week": day_of_week,
                    "month": month,
                    "is_weekend": weekend,
                    "is_rush_hour": rush
                })
            current_time += timedelta(hours=1)
            
        traffic_df = pd.DataFrame(traffic_list)
        traffic_df.to_csv(os.path.join(self.output_dir, "historical_traffic.csv"), index=False)
        logger.info(f"Saved {len(traffic_df)} traffic records.")
        
        # 5. Generate Ride Requests
        # Let's say ~30 ride requests are made every hour across the city
        ride_list = []
        current_time = start_time
        
        while current_time <= end_time:
            hour = current_time.hour
            rush = is_rush_hour(hour)
            weekend = is_weekend(current_time.weekday())
            
            num_rides = int(random.uniform(5, 15))
            if rush:
                num_rides = int(random.uniform(15, 35))
            elif weekend:
                num_rides = int(random.uniform(10, 20))
                
            for _ in range(num_rides):
                pickup_road = random.choice(roads_list)
                dropoff_road = random.choice(roads_list)
                
                # Coordinate dispersion
                p_lat = pickup_road["length_km"] * random.uniform(-0.005, 0.005) + self.roads[pickup_road["road_id"]-1]["lat"]
                p_lon = pickup_road["length_km"] * random.uniform(-0.005, 0.005) + self.roads[pickup_road["road_id"]-1]["lon"]
                d_lat = dropoff_road["length_km"] * random.uniform(-0.005, 0.005) + self.roads[dropoff_road["road_id"]-1]["lat"]
                d_lon = dropoff_road["length_km"] * random.uniform(-0.005, 0.005) + self.roads[dropoff_road["road_id"]-1]["lon"]
                
                # Haversine distance
                # Calculate simple distance
                d_lat_rad = np.radians(d_lat - p_lat)
                d_lon_rad = np.radians(d_lon - p_lon)
                a = np.sin(d_lat_rad/2)**2 + np.cos(np.radians(p_lat)) * np.cos(np.radians(d_lat)) * np.sin(d_lon_rad/2)**2
                dist_km = 6371.0 * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
                dist_km = max(0.5, round(dist_km, 2))
                
                duration = dist_km * random.uniform(1.8, 3.5) # minutes per km
                duration = max(2.0, round(duration, 1))
                
                fare = 15.0 + dist_km * 7.5 + duration * 1.5
                status = random.choices(["COMPLETED", "CANCELLED", "NO_SHOW"], weights=[0.85, 0.12, 0.03])[0]
                
                # Random minutage within the hour
                ride_time = current_time + timedelta(minutes=random.randint(0, 59))
                
                ride_list.append({
                    "timestamp": ride_time.isoformat(),
                    "pickup_latitude": round(p_lat, 6),
                    "pickup_longitude": round(p_lon, 6),
                    "dropoff_latitude": round(d_lat, 6),
                    "dropoff_longitude": round(d_lon, 6),
                    "pickup_road_id": pickup_road["road_id"],
                    "distance_km": round(dist_km, 2),
                    "duration_minutes": round(duration, 1),
                    "fare_amount": round(fare, 2),
                    "status": status
                })
            current_time += timedelta(hours=1)
            
        rides_df = pd.DataFrame(ride_list)
        rides_df.to_csv(os.path.join(self.output_dir, "historical_ride_requests.csv"), index=False)
        logger.info(f"Saved {len(rides_df)} ride request records.")
        logger.info("Historical data generation complete!")

if __name__ == '__main__':
    generator = HistoricalDataGenerator()
    generator.generate_all_data(days=30) # Let's generate 30 days of data for smaller files
