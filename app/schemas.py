# app/schemas.py
from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict, Any, List

class PredictIn(BaseModel):
    date: str = Field(..., example="2025-01-15")
    tmax: float
    tmin: float
    humidity: float = Field(..., ge=0, le=100)   # %
    wind: float                                   # km/h
    rain_24h: float = 0.0
    rain_7d: Optional[float] = None
    rain_30d: Optional[float] = None

    # 🔁 Acepta alias: tmax_c, tmin_c, rh_pct, wind_kmh, rain_mm, rain, etc.
    @model_validator(mode="before")
    def _aliases(cls, v):
        if isinstance(v, dict):
            v = v.copy()
            # temperaturas
            if "tmax" not in v and "tmax_c" in v:
                v["tmax"] = v["tmax_c"]
            if "tmin" not in v and "tmin_c" in v:
                v["tmin"] = v["tmin_c"]
            # humedad
            if "humidity" not in v:
                if "rh_pct" in v:
                    v["humidity"] = v["rh_pct"]
                elif "rh" in v:
                    v["humidity"] = v["rh"]
            # viento
            if "wind" not in v:
                if "wind_kmh" in v:
                    v["wind"] = v["wind_kmh"]
                elif "wind_ms" in v:
                    # si te pasan m/s, conviértelo a km/h
                    try:
                        v["wind"] = float(v["wind_ms"]) * 3.6
                    except Exception:
                        pass
            # lluvia
            if "rain_24h" not in v:
                if "rain_mm" in v:
                    v["rain_24h"] = v["rain_mm"]
                elif "rain" in v:
                    v["rain_24h"] = v["rain"]
            return v
        return v

class PredictOut(BaseModel):
    probability: float = Field(..., ge=0, le=1)
    probability_pct: float = Field(..., ge=0, le=100)
    probability_pct_str: str
    probability_pct_str_es: str
    interpretation: str
    analyzed_data: Dict[str, Any]
    chart_png_base64: Optional[str] = None

# Salida para rango (como ya la tienes)
class PredictPoint(BaseModel):
    date: str
    probability: float
    probability_pct: float

class RangeOut(BaseModel):
    start: str
    end: str
    points: List[PredictPoint]
    chart_png_base64: Optional[str] = None
    city: str
