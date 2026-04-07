# app/main.py
import io
import os
import json
import base64
from datetime import date as _date

import pandas as pd
import matplotlib.pyplot as plt
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.schemas import PredictIn, PredictOut, RangeOut
from app.service.predict import score_payload
from src.ml.train import train_and_save
from src.utils.paths import META_PATH
from src.db.session import engine
from app.auth import require_admin_db

# ---------- util gráfico ---------------
def prob_plot_b64(title: str, prob: float) -> str:
    fig, ax = plt.subplots()
    ax.bar([title], [prob])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Probabilidad")
    ax.set_title("Riesgo estimado")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

# ---------- FastAPI --------------------
app = FastAPI(
    title="Forest Fire Risk",
    version="1.3.0",
    description="API de predicción de incendios (Random Forest + FFWI) con soporte de localidades."
)

# CORS para Vite/React  (nunca usar "*" con allow_credentials=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        os.getenv("CORS_ORIGIN", ""),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- endpoints ------------------
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/locations")
def locations():
    with engine.connect() as con:
        rows = con.execute(text("SELECT DISTINCT city FROM climatic_data ORDER BY city")).fetchall()
    return {"locations": [r[0] for r in rows]}

@app.get("/days")
def list_days(city: str = Query("tunja")):
    """Lista de fechas disponibles por localidad."""
    with engine.connect() as con:
        rows = con.execute(
            text("SELECT date FROM climatic_data WHERE city=:c ORDER BY date"),
            {"c": city}
        ).fetchall()
    return {"city": city, "dates": [r[0].isoformat() for r in rows]}

@app.post("/train", dependencies=[Depends(require_admin_db)])
def train():
    """Re-entrena el modelo con todo lo cargado en BD (solo admin)."""
    try:
        return train_and_save()
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno al entrenar el modelo.")

@app.post("/predict", response_model=PredictOut)
def predict(item: PredictIn):
    """
    Simulador manual. La fecha es opcional (se usa hoy para la etiqueta del gráfico).
    No se calculan acumulados desde la BD; si no pasas rain_7d/rain_30d, el modelo usa lo que tenga definido.
    """
    payload = item.model_dump()
    if not payload.get("date"):
        payload["date"] = _date.today().isoformat()

    try:
        res = score_payload(payload)
        res["chart_png_base64"] = prob_plot_b64(payload["date"], res["probability"])
        return res
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="No se encontró el modelo. Entrena primero con POST /train.")
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno al procesar la predicción.")

@app.get("/predict/by-date", response_model=PredictOut)
def predict_by_date(
    date: str = Query(..., description="YYYY-MM-DD"),
    city: str = Query("tunja")
):
    """
    Predicción para un día de la BD (por localidad).
    Obtiene tmax/tmin/RH/viento/lluvia, calcula acumulados 7/30 días y predice.
    """
    try:
        with engine.connect() as con:
            row = con.execute(text("""
                SELECT date, tmax_c, tmin_c, rh_pct, wind_kmh, rain_mm
                FROM climatic_data
                WHERE date = :d AND city = :c
            """), {"d": date, "c": city}).fetchone()
            if not row:
                raise HTTPException(404, f"No hay datos para {date} en {city}")

            acc = con.execute(text("""
                SELECT
                  SUM(rain_mm) FILTER (WHERE date BETWEEN CAST(:d AS DATE) - INTERVAL '6 days' AND CAST(:d AS DATE) AND city=:c) AS rain_7d,
                  SUM(rain_mm) FILTER (WHERE date BETWEEN CAST(:d AS DATE) - INTERVAL '29 days' AND CAST(:d AS DATE) AND city=:c) AS rain_30d
                FROM climatic_data
            """), {"d": date, "c": city}).fetchone()

        payload = {
            "date": row[0].isoformat(),
            "tmax": float(row[1]),
            "tmin": float(row[2]),
            "humidity": float(row[3]),
            "wind": float(row[4]),
            "rain_24h": float(row[5]),
            "rain_7d": float(acc[0] or 0.0),
            "rain_30d": float(acc[1] or 0.0),
        }
        res = score_payload(payload)
        res["chart_png_base64"] = prob_plot_b64(f"{date} ({city})", res["probability"])
        return res

    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="No se encontró el modelo. Entrena primero.")
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno al procesar la predicción.")

@app.get("/predict/range", response_model=RangeOut)
def predict_range(
    start: str = Query(..., description="YYYY-MM-DD"),
    end: str = Query(..., description="YYYY-MM-DD"),
    city: str = Query("tunja")
):
    """
    Serie de probabilidad (%) por día entre [start, end] para una localidad.
    """
    s = pd.to_datetime(start); e = pd.to_datetime(end)
    if s > e:
        raise HTTPException(400, "start debe ser <= end")

    s_pad = (s - pd.Timedelta(days=29)).strftime("%Y-%m-%d")
    with engine.connect() as con:
        df = pd.read_sql(
            text("""SELECT date, tmax_c, tmin_c, rh_pct, wind_kmh, rain_mm
                    FROM climatic_data
                    WHERE city=:c AND date BETWEEN :s AND :e
                    ORDER BY date"""),
            con, params={"c": city, "s": s_pad, "e": end}
        )
    if df.empty:
        return {"city": city, "start": start, "end": end, "points": []}

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df["rain_7d"]  = df["rain_mm"].rolling(7,  min_periods=1).sum()
    df["rain_30d"] = df["rain_mm"].rolling(30, min_periods=1).sum()

    out = []
    for _, r in df[df["date"].between(s, e)].iterrows():
        payload = {
            "date": r["date"].date().isoformat(),
            "tmax": float(r["tmax_c"]),
            "tmin": float(r["tmin_c"]),
            "humidity": float(r["rh_pct"]),
            "wind": float(r["wind_kmh"]),
            "rain_24h": float(r["rain_mm"]),
            "rain_7d": float(r["rain_7d"]),
            "rain_30d": float(r["rain_30d"]),
        }
        res = score_payload(payload)
        out.append({
            "date": payload["date"],
            "probability": res["probability"],
            "probability_pct": res["probability_pct"],
        })

    return {"city": city, "start": start, "end": end, "points": out}

@app.get("/model/info")
def model_info():
    try:
        with open(META_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Aún no hay metadata. Entrena el modelo.")
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno al leer metadata del modelo.")
