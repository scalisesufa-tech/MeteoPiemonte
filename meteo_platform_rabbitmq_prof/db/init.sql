CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS meteo_observation (
  id BIGSERIAL PRIMARY KEY,
  station_id TEXT,
  station_name TEXT,
  city TEXT,
  lat DOUBLE PRECISION,
  lon DOUBLE PRECISION,
  observed_at TIMESTAMP NOT NULL,
  temperature DOUBLE PRECISION,
  relative_humidity DOUBLE PRECISION,
  pressure DOUBLE PRECISION,
  raw_json TEXT
);

SELECT create_hypertable('meteo_observation', 'observed_at', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_meteo_station_time ON meteo_observation (station_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_meteo_city ON meteo_observation (city);
