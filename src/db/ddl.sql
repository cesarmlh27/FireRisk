-- tabla de datos climáticos
CREATE TABLE IF NOT EXISTS climatic_data (
  id        BIGSERIAL PRIMARY KEY,
  city      VARCHAR(100) NOT NULL DEFAULT 'tunja',
  date      DATE NOT NULL,
  year      INT NOT NULL,
  doy       INT NOT NULL,
  tmean_c   NUMERIC(6,2) NOT NULL,
  tmax_c    NUMERIC(6,2) NOT NULL,
  tmin_c    NUMERIC(6,2) NOT NULL,
  rh_pct    NUMERIC(6,2) NOT NULL,
  wind_ms   NUMERIC(8,3) NOT NULL,
  wind_kmh  NUMERIC(8,2) GENERATED ALWAYS AS (wind_ms*3.6) STORED,
  rain_mm   NUMERIC(8,2) NOT NULL,
  CONSTRAINT uq_city_date UNIQUE (city, date)
);

CREATE INDEX IF NOT EXISTS idx_climatic_data_city_date ON climatic_data(city, date);

-- tabla de usuarios / API keys (SHA-256, hex)
CREATE TABLE IF NOT EXISTS app_user (
  id            BIGSERIAL PRIMARY KEY,
  username      VARCHAR(100) NOT NULL UNIQUE,
  api_key_sha   CHAR(64)    NOT NULL UNIQUE,  -- SHA-256 hex de la API key
  role          VARCHAR(50) NOT NULL DEFAULT 'viewer'
);

-- usuario admin por defecto (API key = "changeme")
-- Reemplaza el hash ejecutando:
--   python -c "import hashlib; print(hashlib.sha256(b'<tu-api-key>').hexdigest())"
INSERT INTO app_user (username, api_key_sha, role)
VALUES (
  'admin',
  '7f86ea16be3ffe73b56ffe25e679b4d1e82ba60b7cd1f61e5e70e7e12e547ba2',  -- "changeme"
  'admin'
)
ON CONFLICT (username) DO NOTHING;
