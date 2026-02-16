from src.ml.infer import predict_proba
from src.ml.indices import compute_ffwi_row

def score_payload(payload: dict) -> dict:
    try:
        p = float(predict_proba(payload))
    except Exception:
        p = 0.5
    if not (0.0 <= p <= 1.0):
        p = 0.5

    pct = p * 100.0
    if p < 0.2:        interp = "Bajo"
    elif p <= 0.5:     interp = "Moderado"   # <= 0.5 se considera Moderado
    elif p < 0.8:      interp = "Alto"
    else:              interp = "Muy Alto"

    tmax = float(payload["tmax"]); tmin = float(payload["tmin"])
    tmean = (tmax + tmin) / 2.0
    ffwi = compute_ffwi_row(tmean, float(payload["humidity"]), float(payload["wind"]))

    analyzed = {
        "date": payload["date"],
        "tmax_c": tmax, "tmin_c": tmin, "tmean_c": tmean,
        "rh_pct": float(payload["humidity"]),
        "wind_kmh": float(payload["wind"]),
        "rain_24h_mm": float(payload.get("rain_24h", 0.0) or 0.0),
        "rain_7d_mm": float(payload.get("rain_7d", 0.0) or 0.0),
        "rain_30d_mm": float(payload.get("rain_30d", 0.0) or 0.0),
        "ffwi": float(ffwi)
    }

    return {
        "probability": p,
        "probability_pct": round(pct, 6),
        "probability_pct_str": f"{pct:.6f}%",
        "probability_pct_str_es": f"{pct:.6f}%".replace(".", ","),
        "interpretation": interp,
        "analyzed_data": analyzed
    }
