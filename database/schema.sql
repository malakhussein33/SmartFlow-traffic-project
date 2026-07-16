-- SQL Schema for Smart City Traffic Management Database
-- Database: smartcity

CREATE TABLE IF NOT EXISTS roads (
    road_id SERIAL PRIMARY KEY,
    road_name VARCHAR(100) UNIQUE NOT NULL,
    road_type VARCHAR(50),
    length_km FLOAT NOT NULL,
    num_lanes INT NOT NULL,
    speed_limit_kmh INT NOT NULL,
    city VARCHAR(50) DEFAULT 'Cairo',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sensor_locations (
    sensor_id VARCHAR(50) PRIMARY KEY,
    road_id INT REFERENCES roads(road_id) ON DELETE CASCADE,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    installation_date DATE DEFAULT CURRENT_DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS weather_data (
    weather_id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    temperature_celsius FLOAT NOT NULL,
    humidity_percent FLOAT NOT NULL,
    rain_mm FLOAT NOT NULL,
    wind_speed_kmh FLOAT NOT NULL,
    weather_condition VARCHAR(50) NOT NULL,
    city VARCHAR(50) DEFAULT 'Cairo',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS traffic_events (
    event_id SERIAL PRIMARY KEY,
    sensor_id VARCHAR(50) REFERENCES sensor_locations(sensor_id) ON DELETE CASCADE,
    road_id INT REFERENCES roads(road_id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL,
    vehicle_count INT NOT NULL,
    average_speed_kmh FLOAT NOT NULL,
    traffic_density FLOAT NOT NULL,
    congestion_index FLOAT NOT NULL,
    congestion_level VARCHAR(20) NOT NULL,
    weather_id INT REFERENCES weather_data(weather_id) ON DELETE SET NULL,
    hour INT NOT NULL,
    day_of_week INT NOT NULL,
    month INT NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    is_rush_hour BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ride_requests (
    request_id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    pickup_latitude FLOAT NOT NULL,
    pickup_longitude FLOAT NOT NULL,
    dropoff_latitude FLOAT NOT NULL,
    dropoff_longitude FLOAT NOT NULL,
    pickup_road_id INT REFERENCES roads(road_id) ON DELETE SET NULL,
    distance_km FLOAT NOT NULL,
    duration_minutes FLOAT NOT NULL,
    fare_amount FLOAT NOT NULL,
    status VARCHAR(20) NOT NULL, -- COMPLETED, CANCELLED, NO_SHOW
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS predictions (
    prediction_id SERIAL PRIMARY KEY,
    model_name VARCHAR(50) NOT NULL,
    prediction_type VARCHAR(50) NOT NULL, -- CONGESTION, VEHICLE_COUNT, RIDE_DEMAND
    road_id INT REFERENCES roads(road_id) ON DELETE CASCADE,
    sensor_id VARCHAR(50) REFERENCES sensor_locations(sensor_id) ON DELETE CASCADE,
    predicted_at TIMESTAMPTZ NOT NULL,
    prediction_horizon_minutes INT NOT NULL,
    predicted_vehicle_count INT,
    predicted_congestion_level VARCHAR(20),
    predicted_avg_speed FLOAT,
    confidence_score FLOAT,
    actual_vehicle_count INT,
    actual_congestion_level VARCHAR(20),
    rmse FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS batch_reports (
    report_id SERIAL PRIMARY KEY,
    report_type VARCHAR(20) NOT NULL, -- DAILY, WEEKLY, MONTHLY
    report_date DATE NOT NULL,
    road_id INT REFERENCES roads(road_id) ON DELETE CASCADE,
    avg_speed FLOAT NOT NULL,
    total_vehicles BIGINT NOT NULL,
    peak_hour INT NOT NULL,
    congestion_hours INT NOT NULL,
    congestion_score FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- CREATE INDEXES FOR FAST RETRIEVAL
CREATE INDEX IF NOT EXISTS idx_traffic_events_timestamp ON traffic_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_traffic_events_road_id ON traffic_events(road_id);
CREATE INDEX IF NOT EXISTS idx_traffic_events_sensor_id ON traffic_events(sensor_id);
CREATE INDEX IF NOT EXISTS idx_weather_data_timestamp ON weather_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_ride_requests_timestamp ON ride_requests(timestamp);
CREATE INDEX IF NOT EXISTS idx_predictions_predicted_at ON predictions(predicted_at);
CREATE INDEX IF NOT EXISTS idx_predictions_road_id ON predictions(road_id);

-- VIEWS FOR STREAMLIT DASHBOARD
CREATE OR REPLACE VIEW v_current_traffic_status AS
SELECT DISTINCT ON (te.sensor_id)
    te.sensor_id,
    r.road_name,
    sl.latitude,
    sl.longitude,
    te.timestamp,
    te.vehicle_count,
    te.average_speed_kmh,
    te.congestion_index,
    te.congestion_level,
    w.weather_condition,
    w.temperature_celsius
FROM traffic_events te
JOIN roads r ON te.road_id = r.road_id
JOIN sensor_locations sl ON te.sensor_id = sl.sensor_id
LEFT JOIN weather_data w ON te.weather_id = w.weather_id
ORDER BY te.sensor_id, te.timestamp DESC;

CREATE OR REPLACE VIEW v_road_congestion_summary AS
SELECT 
    r.road_name,
    r.speed_limit_kmh,
    ROUND(AVG(te.average_speed_kmh)::numeric, 2) as avg_speed,
    ROUND(AVG(te.vehicle_count)::numeric, 2) as avg_vehicle_count,
    ROUND(AVG(te.congestion_index)::numeric, 2) as avg_congestion_index,
    COUNT(CASE WHEN te.congestion_level = 'CRITICAL' THEN 1 END) as critical_events_count
FROM traffic_events te
JOIN roads r ON te.road_id = r.road_id
WHERE te.timestamp > NOW() - INTERVAL '24 HOURS'
GROUP BY r.road_name, r.speed_limit_kmh;
