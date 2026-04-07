# 🔥 FireRisk — Forest Fire Risk Prediction

Sistema de predicción de riesgo de incendio forestal para **Tunja, Colombia**, basado en datos climáticos históricos de NASA POWER y un modelo de Random Forest calibrado.

---

## Stack

| Capa | Tecnología |
|---|---|
| Backend API | Python · FastAPI · Uvicorn |
| Base de datos | PostgreSQL · SQLAlchemy 2.0 |
| Machine Learning | scikit-learn (RandomForest + CalibratedClassifierCV) |
| Índice de fuego | FFWI (Fosberg Fire Weather Index) |
| Frontend | React 19 · Recharts · Vite 7 |

---

## Estructura del proyecto

```
ForestFire-app/
├── app/                    # API FastAPI
│   ├── main.py             # Endpoints: /predict, /predict/by-date, /predict/range, /train …
│   ├── auth.py             # Autenticación por API key (SHA-256 + hmac)
│   ├── schemas.py          # Modelos Pydantic de entrada/salida
│   └── service/
│       └── predict.py      # Lógica de puntuación y etiquetado
├── src/
│   ├── db/
│   │   ├── ddl.sql         # Schema de PostgreSQL (climatic_data + app_user)
│   │   └── session.py      # Engine compartido con pool de conexiones
│   ├── etl/
│   │   └── load_to_db.py   # Carga del CSV NASA POWER → PostgreSQL
│   ├── ml/
│   │   ├── features.py     # Feature engineering + etiquetado adaptativo
│   │   ├── indices.py      # Cálculo del FFWI
│   │   ├── infer.py        # Inferencia con el modelo entrenado
│   │   └── train.py        # Entrenamiento y guardado del modelo
│   └── utils/
│       └── paths.py        # Variables de entorno y rutas de archivos
├── frontend/               # React + Vite
│   └── src/
│       └── App.jsx         # SPA con 3 tabs: Histórico / Simulador / Serie
├── models/                 # Artefactos ML (generados por /train)
│   ├── model.joblib
│   ├── features.json
│   ├── metadata.json
│   └── latest/             # Copia sincronizada del último entrenamiento
└── data/
    └── raw/
        └── Base_de_Datos_Tunja_clima.csv
```

---

## Requisitos previos

- Python ≥ 3.11
- Node.js ≥ 18
- PostgreSQL ≥ 14

---

## Instalación y puesta en marcha

### 1 — Clonar el repositorio

```bash
git clone https://github.com/cesarmlh27/FireRisk.git
cd FireRisk
```

### 2 — Backend (Python)

```bash
# Crear y activar entorno virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt
```

### 3 — Variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
PGHOST=localhost
PGPORT=5432
PGUSER=postgres
PGPASSWORD=tu_password
PGDATABASE=forestfire

# Origen del frontend (para CORS)
CORS_ORIGIN=http://localhost:5173
```

### 4 — Base de datos

```bash
# Crear la base de datos
psql -U postgres -c "CREATE DATABASE forestfire;"

# Aplicar el schema
psql -U postgres -d forestfire -f src/db/ddl.sql
```

El DDL crea:
- `climatic_data` — datos climáticos por ciudad y fecha
- `app_user` — usuario admin por defecto con API key `changeme`

> **Importante:** Cambia la API key de admin antes de usar en producción.
> Genera el hash con:
> ```bash
> python -c "import hashlib; print(hashlib.sha256(b'tu-api-key').hexdigest())"
> ```
> Y actualiza la fila en `app_user`.

### 5 — Cargar datos climáticos

```bash
python -m src.etl.load_to_db
```

Carga el CSV de NASA POWER (`data/raw/`) en PostgreSQL (~1 150 filas, 2022–2025).

### 6 — Entrenar el modelo

```bash
# Opción A: línea de comandos
python -m src.ml.train

# Opción B: endpoint de la API (requiere la API key de admin)
curl -X POST http://localhost:8000/train -H "X-API-Key: changeme"
```

Genera `models/model.joblib`, `models/features.json` y `models/metadata.json`.

### 7 — Levantar el backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Documentación interactiva: [http://localhost:8000/docs](http://localhost:8000/docs)

### 8 — Levantar el frontend

```bash
cd frontend
npm install
npm run dev
```

App disponible en: [http://localhost:5173](http://localhost:5173)

---

## Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Estado de la API |
| `GET` | `/locations` | Ciudades disponibles en BD |
| `GET` | `/days?city=tunja` | Fechas disponibles por ciudad |
| `POST` | `/predict` | Predicción manual (parámetros en body) |
| `GET` | `/predict/by-date?date=YYYY-MM-DD&city=tunja` | Predicción para una fecha de la BD |
| `GET` | `/predict/range?start=...&end=...&city=tunja` | Serie de probabilidades por rango |
| `POST` | `/train` | Re-entrenamiento (requiere `X-API-Key`) |
| `GET` | `/model/info` | Metadata del modelo actual |

---

## Ejemplo de predicción manual

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-07-15",
    "tmax": 22.5,
    "tmin": 8.0,
    "humidity": 45.0,
    "wind": 18.0,
    "rain_24h": 0.0
  }'
```

Respuesta:
```json
{
  "probability": 0.73,
  "probability_pct": 73.0,
  "interpretation": "Alto",
  "analyzed_data": { "..." : "..." }
}
```

---

## Modelo de Machine Learning

- **Algoritmo:** `RandomForestClassifier` (500 árboles) calibrado con `CalibratedClassifierCV(method="sigmoid", cv=3)`
- **Features (12):** `tmax_c`, `tmin_c`, `tmean_c`, `dtr`, `rh_pct`, `wind_kmh`, `rain_mm`, `rain_7d`, `rain_30d`, `doy_sin`, `doy_cos`, `ffwi`
- **Etiquetado:** Heurístico adaptativo por percentiles del dataset (p80 de tmax, p25 de RH, p70 de viento) — garantiza 5–10 % de días positivos
- **Índice FFWI:** Fosberg Fire Weather Index ajustado a temperatura media

---

## Seguridad implementada

- API key de admin comparada con `hmac.compare_digest` (resistente a timing attacks)
- Hash SHA-256 almacenado en BD, nunca la key en texto plano
- CORS restringido a orígenes explícitos (sin wildcard `*`)
- Errores internos no expuestos al cliente
- API key temporal en `sessionStorage` (se borra al cerrar el tab)

---

## Licencia

Proyecto académico — uso educativo.
