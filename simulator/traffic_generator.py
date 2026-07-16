"""
Traffic Data Simulator
======================
Simulates real-time traffic sensor data for Cairo and publishes events to Apache Kafka.
"""
import os
import sys
import json
import time
import random
from datetime import datetime, timezone
from typing import Dict, Any, List
from dotenv import load_dotenv

# Temporarily remove local directories to import the external kafka-python package
local_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
current_dir = os.path.dirname(os.path.abspath(__file__))
cwd = os.getcwd()

saved_paths = []
for p in list(sys.path):
    if p in [local_path, current_dir, cwd, '']:
        sys.path.remove(p)
        saved_paths.append(p)

from kafka import KafkaProducer

# Restore sys.path
for p in saved_paths:
    sys.path.insert(0, p)

sys.path.insert(0, local_path)
from utils.helpers import load_config, validate_coordinates, calculate_traffic_density, calculate_congestion_index, get_congestion_level, is_rush_hour, is_weekend
from utils.logger import get_logger

logger = get_logger("traffic_generator")
load_dotenv()

class TrafficSimulator:
    def __init__(self, config_path: str = "./config/config.yaml"):
        self.config = load_config(config_path)
        self.bootstrap_servers = self.config['kafka']['bootstrap_servers']
        self.topic = self.config['kafka']['topics']['traffic']
        self.roads = self.config['simulation']['roads']
        self.producer = self._create_producer()
        
    def _create_producer(self) -> KafkaProducer:
        retries = 0
        while retries < 5:
            try:
                producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    acks='all',
                    retries=5
                )
                logger.info("Kafka Producer successfully initialized for traffic simulator.")
                return producer
            except Exception as e:
                retries += 1
                logger.warning(f"Failed to connect to Kafka. Retrying {retries}/5 in 5 seconds... Error: {e}")
                time.sleep(5)
        logger.critical("Failed to connect to Kafka after 5 attempts. Exiting.")
        sys.exit(1)
        
    def _get_current_weather(self) -> Dict[str, Any]:
        # Simulating external weather source
        temp = random.uniform(15.0, 45.0)
        humidity = random.uniform(40.0, 85.0)
        rain = random.choices([0.0, 0.5, 2.0, 10.0], weights=[0.95, 0.03, 0.015, 0.005])[0]
        wind = random.uniform(5.0, 30.0)
        conditions = "Sunny"
        if rain > 0:
            conditions = "Rainy" if rain > 2 else "Drizzle"
        elif temp > 38:
            conditions = "Heatwave"
        return {
            "temperature": temp,
            "humidity": humidity,
            "rain_mm": rain,
            "wind_speed_kmh": wind,
            "weather_condition": conditions
        }

    def simulate_event(self, road: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        hour = now.hour
        day_of_week = now.weekday()
        
        # Rush Hour / Weekend multipliers
        rush = is_rush_hour(hour)
        weekend = is_weekend(day_of_week)
        
        # Base Vehicle calculation
        base_capacity = road['lanes'] * 150 # capacity per kilometer lane
        if rush:
            vehicle_factor = random.uniform(0.7, 1.2)
        elif weekend:
            vehicle_factor = random.uniform(0.2, 0.5)
        else:
            vehicle_factor = random.uniform(0.4, 0.8)
            
        # Night quiet hours (11 PM - 5 AM)
        if 23 <= hour or hour <= 5:
            vehicle_factor = random.uniform(0.05, 0.2)
            
        vehicle_count = int(base_capacity * vehicle_factor)
        
        # Speed calculations based on vehicle count
        # Higher count -> lower speed
        speed_factor = 1.0 - (vehicle_count / (base_capacity * 1.5))
        speed_factor = max(0.1, min(1.1, speed_factor))
        
        avg_speed = road['speed_limit'] * speed_factor
        # Add minor random noise
        avg_speed += random.uniform(-5.0, 5.0)
        avg_speed = max(5.0, min(road['speed_limit'] * 1.2, avg_speed))
        
        density = calculate_traffic_density(vehicle_count, 1.0, road['lanes'])
        congestion_index = calculate_congestion_index(avg_speed, road['speed_limit'])
        congestion_level = get_congestion_level(congestion_index)
        
        weather = self._get_current_weather()
        
        sensor_id = f"SENSOR_{road['name'].replace(' ', '_').upper()}_01"
        
        event = {
            "sensor_id": sensor_id,
            "road_name": road['name'],
            "latitude": road['lat'],
            "longitude": road['lon'],
            "vehicle_count": vehicle_count,
            "average_speed_kmh": round(avg_speed, 2),
            "traffic_density": round(density, 2),
            "congestion_index": round(congestion_index, 2),
            "congestion_level": congestion_level,
            "weather_condition": weather["weather_condition"],
            "temperature": round(weather["temperature"], 1),
            "humidity": round(weather["humidity"], 1),
            "rain_mm": round(weather["rain_mm"], 2),
            "wind_speed_kmh": round(weather["wind_speed_kmh"], 2),
            "timestamp": now.isoformat(),
            "hour": hour,
            "day_of_week": day_of_week,
            "month": now.month,
            "is_weekend": weekend,
            "is_rush_hour": rush
        }
        return event

    def run(self, interval: int = 1):
        logger.info(f"Starting traffic simulation. Sending events every {interval}s...")
        try:
            while True:
                for road in self.roads:
                    event = self.simulate_event(road)
                    self.producer.send(self.topic, value=event)
                logger.info(f"Published {len(self.roads)} traffic events to Kafka.")
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Simulation stopped by user.")
        finally:
            self.producer.close()
            logger.info("Producer closed.")

if __name__ == '__main__':
    sim = TrafficSimulator()
    sim.run()
