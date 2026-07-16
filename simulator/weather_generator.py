"""
Weather Data Simulator
======================
Simulates real-time weather reports for Cairo and publishes to Apache Kafka.
"""
import os
import sys
import json
import time
import random
from datetime import datetime, timezone
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
from utils.helpers import load_config
from utils.logger import get_logger

logger = get_logger("weather_generator")
load_dotenv()

class WeatherSimulator:
    def __init__(self, config_path: str = "./config/config.yaml"):
        self.config = load_config(config_path)
        self.bootstrap_servers = self.config['kafka']['bootstrap_servers']
        self.topic = self.config['kafka']['topics']['weather']
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
                logger.info("Kafka Producer successfully initialized for weather simulator.")
                return producer
            except Exception as e:
                retries += 1
                logger.warning(f"Failed to connect to Kafka. Retrying {retries}/5 in 5 seconds... Error: {e}")
                time.sleep(5)
        logger.critical("Failed to connect to Kafka after 5 attempts. Exiting.")
        sys.exit(1)
        
    def generate_weather(self) -> dict:
        now = datetime.now(timezone.utc)
        hour = now.hour
        month = now.month
        
        # Determine base temperature based on month (Cairo averages)
        # Summer (June, July, August) -> 35-43°C
        # Winter (December, January, February) -> 12-20°C
        if month in [6, 7, 8]:
            base_temp = 34.0
        elif month in [12, 1, 2]:
            base_temp = 15.0
        else:
            base_temp = 25.0
            
        # Diurnal temperature variation
        # Warmer in afternoon (12-16), cooler at night (2-5)
        if 12 <= hour <= 16:
            temp = base_temp + random.uniform(4.0, 8.0)
        elif 2 <= hour <= 5:
            temp = base_temp - random.uniform(4.0, 8.0)
        else:
            temp = base_temp + random.uniform(-2.0, 2.0)
            
        humidity = random.uniform(35.0, 80.0)
        # Cairo is arid; rain is extremely rare
        rain_prob = random.random()
        rain = 0.0
        if rain_prob > 0.98:
            rain = random.uniform(1.0, 15.0)
            
        wind = random.uniform(5.0, 35.0)
        
        conditions = "Sunny"
        if rain > 0:
            conditions = "Rainy" if rain > 5.0 else "Drizzle"
        elif humidity > 75.0 and temp < 18.0:
            conditions = "Foggy"
        elif wind > 25.0 and temp > 35.0:
            conditions = "Sandstorm"
            
        return {
            "timestamp": now.isoformat(),
            "temperature_celsius": round(temp, 1),
            "humidity_percent": round(humidity, 1),
            "rain_mm": round(rain, 2),
            "wind_speed_kmh": round(wind, 2),
            "weather_condition": conditions,
            "city": "Cairo"
        }
        
    def run(self, interval: int = 30):
        logger.info(f"Starting weather simulation. Sending reports every {interval}s...")
        try:
            while True:
                event = self.generate_weather()
                self.producer.send(self.topic, value=event)
                logger.info(f"Published weather report: {event['weather_condition']} ({event['temperature_celsius']}°C)")
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Weather simulator stopped by user.")
        finally:
            self.producer.close()
            logger.info("Weather producer closed.")

if __name__ == '__main__':
    sim = WeatherSimulator()
    sim.run()
