CREATE TABLE IF NOT EXISTS climatic_data (
  id        BIGSERIAL PRIMARY KEY,
  date      DATE UNIQUE NOT NULL,
  year      INT NOT NULL,
  doy       INT NOT NULL,
  tmean_c   NUMERIC(6,2) NOT NULL,
  tmax_c    NUMERIC(6,2) NOT NULL,
  tmin_c    NUMERIC(6,2) NOT NULL,
  rh_pct    NUMERIC(6,2) NOT NULL,
  wind_ms   NUMERIC(8,3) NOT NULL,
  wind_kmh  NUMERIC(8,2) GENERATED ALWAYS AS (wind_ms*3.6) STORED,
  rain_mm   NUMERIC(8,2) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_climatic_data_date ON climatic_data(date);
