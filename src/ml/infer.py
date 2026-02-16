import json, joblib, numpy as np, pandas as pd
from src.utils.paths import MODEL_PATH, FEATURES_PATH
from src.ml.indices import compute_ffwi_row

def _load():
    clf = joblib.load(MODEL_PATH)
    with open(FEATURES_PATH, "r", encoding="utf-8") as f:
        feats = json.load(f)["feature_cols"]
    return clf, feats

def _clean_num(x, name):
    if x is None:
        raise ValueError(f"{name} es None")
    try:
        x = float(x)
    except Exception as e:
        raise ValueError(f"{name} inválido: {e}")
    if not np.isfinite(x):
        raise ValueError(f"{name} no es finito")
    return x

def features_from_payload(payload: dict) -> pd.DataFrame:
    date = pd.to_datetime(payload["date"])
    tmax = _clean_num(payload["tmax"], "tmax")
    tmin = _clean_num(payload["tmin"], "tmin")
    rh   = _clean_num(payload["humidity"], "humidity")
    wind = _clean_num(payload["wind"], "wind")
    rain = float(payload.get("rain_24h", 0.0) or 0.0)

    tmean = (tmax + tmin) / 2.0
    dtr   = tmax - tmin
    rain_7d  = float(payload.get("rain_7d", rain) or 0.0)
    rain_30d = float(payload.get("rain_30d", rain) or 0.0)

    doy = date.timetuple().tm_yday
    doy_sin = np.sin(2*np.pi*doy/365.25)
    doy_cos = np.cos(2*np.pi*doy/365.25)

    try:
        ffwi = compute_ffwi_row(tmean, rh, wind)
        if not np.isfinite(ffwi): ffwi = 0.0
    except Exception:
        ffwi = 0.0

    return pd.DataFrame([{
        "tmax_c": tmax, "tmin_c": tmin, "tmean_c": tmean, "dtr": dtr,
        "rh_pct": rh, "wind_kmh": wind, "rain_mm": rain,
        "rain_7d": rain_7d, "rain_30d": rain_30d,
        "doy_sin": float(doy_sin), "doy_cos": float(doy_cos),
        "ffwi": float(ffwi)
    }])

def predict_proba(payload: dict) -> float:
    clf, feats = _load()
    X = features_from_payload(payload)[feats].to_numpy()
    try:
        proba = clf.predict_proba(X)
        classes = np.array(getattr(clf, "classes_", [0,1]))
        if classes.ndim == 0: classes = np.array([classes])
        if len(classes) == 1:
            p = 0.5  # modelo degenerado -> incertidumbre
        else:
            idx1 = int(np.where(classes==1)[0][0]) if (classes==1).any() else int(np.argmax(classes))
            p = float(proba[0, idx1])
    except Exception:
        p = 0.5
    if not (np.isfinite(p) and 0.0 <= p <= 1.0): p = 0.5
    return p
def predict_proba_debug(payload: dict) -> dict:
    info = {"fallback": False, "reason": None, "classes": None, "raw": None, "features": None}
    try:
        clf, feats = _load()
        Xdf = features_from_payload(payload)
        info["features"] = {c: float(Xdf[c].iloc[0]) for c in Xdf.columns}
        X = Xdf[feats].to_numpy()

        try:
            proba = clf.predict_proba(X)
            classes = np.array(getattr(clf, "classes_", [0, 1]))
            info["classes"] = classes.tolist()
            info["raw"] = proba.tolist()
            if classes.ndim == 0:
                classes = np.array([classes])
            if len(classes) == 1:
                info["fallback"] = True
                info["reason"] = "single_class_model"
                return {"p": 0.5, **info}
            idx1 = int(np.where(classes == 1)[0][0]) if (classes == 1).any() else int(np.argmax(classes))
            p = float(proba[0, idx1])
            return {"p": p, **info}
        except Exception as e:
            info["fallback"] = True
            info["reason"] = f"predict_proba_error: {e}"
            return {"p": 0.5, **info}
    except Exception as e:
        info["fallback"] = True
        info["reason"] = f"feature_build_error: {e}"
        return {"p": 0.5, **info}
