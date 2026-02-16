# src/utils/paths.py
import os
from sqlalchemy.engine import URL

PGHOST = os.getenv("PGHOST", "localhost")
PGPORT = int(os.getenv("PGPORT", "5432"))
PGUSER = os.getenv("PGUSER", "postgres")
PGPASSWORD = os.getenv("PGPASSWORD", "1234")  # evita acentos/caracteres raros si puedes
PGDATABASE = os.getenv("PGDATABASE", "forestfire")

# Pasa un URL object (mejor que str para psycopg2 si hay unicode)
DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=PGUSER,
    password=PGPASSWORD,
    host=PGHOST,
    port=PGPORT,
    database=PGDATABASE,
    query={"sslmode": os.getenv("PGSSLMODE", "prefer")},
)

# Directorios de modelos
BASE_MODELS_DIR = os.getenv("MODELS_DIR", os.path.join("models"))
LATEST_DIR = os.path.join(BASE_MODELS_DIR, "latest")

# Archivos por defecto
MODEL_PATH = os.getenv("MODEL_PATH", os.path.join(BASE_MODELS_DIR, "model.joblib"))
FEATURES_PATH = os.getenv("FEATURES_PATH", os.path.join(BASE_MODELS_DIR, "features.json"))
META_PATH = os.getenv("META_PATH", os.path.join(BASE_MODELS_DIR, "meta.json"))

os.makedirs(BASE_MODELS_DIR, exist_ok=True)
os.makedirs(LATEST_DIR, exist_ok=True)
