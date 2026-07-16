-- Seed Data for Smart City Traffic Management Database

-- Seed Roads (Cairo landmarks)
INSERT INTO roads (road_name, road_type, length_km, num_lanes, speed_limit_kmh, city) VALUES
('Tahrir Square', 'Urban', 1.5, 4, 50, 'Cairo'),
('Corniche El Nil', 'Arterial', 12.0, 3, 60, 'Cairo'),
('Ring Road Cairo', 'Highway', 106.0, 4, 90, 'Cairo'),
('Salah Salem', 'Arterial', 18.5, 3, 80, 'Cairo'),
('October 6 Bridge', 'Flyover', 20.5, 3, 60, 'Cairo'),
('Suez Road', 'Highway', 45.0, 4, 100, 'Cairo'),
('Nasr Road', 'Urban', 8.0, 3, 60, 'Cairo'),
('Abbas El Akkad', 'Urban', 4.5, 2, 50, 'Cairo'),
('Hassan El Maamoun', 'Urban', 5.0, 2, 50, 'Cairo'),
('El Haram Street', 'Urban', 9.0, 3, 60, 'Cairo'),
('Pyramids Road', 'Urban', 9.5, 3, 60, 'Cairo'),
('Mohandessin Street', 'Urban', 3.0, 2, 50, 'Cairo'),
('Zamalek Bridge', 'Flyover', 2.0, 2, 50, 'Cairo'),
('Maadi Road', 'Arterial', 7.5, 3, 80, 'Cairo'),
('Heliopolis Main Street', 'Urban', 6.0, 3, 60, 'Cairo')
ON CONFLICT (road_name) DO NOTHING;

-- Seed Sensor Locations
INSERT INTO sensor_locations (sensor_id, road_id, latitude, longitude, is_active) VALUES
('SENSOR_TAHRIR_01', 1, 30.0444, 31.2357, TRUE),
('SENSOR_CORNICHE_01', 2, 30.0400, 31.2280, TRUE),
('SENSOR_RING_01', 3, 30.0120, 31.2050, TRUE),
('SENSOR_SALAH_01', 4, 30.0650, 31.2750, TRUE),
('SENSOR_6OCT_01', 5, 30.0480, 31.2290, TRUE),
('SENSOR_SUEZ_01', 6, 30.0950, 31.3900, TRUE),
('SENSOR_NASR_01', 7, 30.0700, 31.3200, TRUE),
('SENSOR_ABBAS_01', 8, 30.0750, 31.3400, TRUE),
('SENSOR_MAAMOUN_01', 9, 30.0800, 31.3500, TRUE),
('SENSOR_HARAM_01', 10, 30.0030, 31.1850, TRUE),
('SENSOR_PYRAMIDS_01', 11, 30.0090, 31.1900, TRUE),
('SENSOR_MOHANDESSIN_01', 12, 30.0550, 31.2000, TRUE),
('SENSOR_ZAMALEK_01', 13, 30.0570, 31.2200, TRUE),
('SENSOR_MAADI_01', 14, 29.9600, 31.2600, TRUE),
('SENSOR_HELIOPOLIS_01', 15, 30.1000, 31.3300, TRUE)
ON CONFLICT (sensor_id) DO NOTHING;

-- Seed Weather Data
INSERT INTO weather_data (timestamp, temperature_celsius, humidity_percent, rain_mm, wind_speed_kmh, weather_condition) VALUES
(NOW() - INTERVAL '2 HOURS', 32.5, 45.0, 0.0, 12.5, 'Sunny'),
(NOW() - INTERVAL '1 HOURS', 31.0, 48.0, 0.0, 10.0, 'Sunny'),
(NOW(), 30.0, 50.0, 0.0, 9.5, 'Sunny');

-- Seed Ride Requests
INSERT INTO ride_requests (timestamp, pickup_latitude, pickup_longitude, dropoff_latitude, dropoff_longitude, pickup_road_id, distance_km, duration_minutes, fare_amount, status) VALUES
(NOW() - INTERVAL '30 MINUTES', 30.0444, 31.2357, 30.0750, 31.3400, 1, 8.5, 25.0, 75.0, 'COMPLETED'),
(NOW() - INTERVAL '25 MINUTES', 30.0400, 31.2280, 30.0120, 31.2050, 2, 6.2, 18.0, 55.0, 'COMPLETED'),
(NOW() - INTERVAL '20 MINUTES', 30.0650, 31.2750, 30.0950, 31.3900, 4, 15.4, 35.0, 120.0, 'COMPLETED'),
(NOW() - INTERVAL '15 MINUTES', 30.0480, 31.2290, 30.0700, 31.3200, 5, 9.1, 28.0, 80.0, 'COMPLETED'),
(NOW() - INTERVAL '10 MINUTES', 30.0030, 31.1850, 30.0550, 31.2000, 10, 7.8, 22.0, 70.0, 'COMPLETED');
