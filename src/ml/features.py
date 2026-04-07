import numpy as np
import pandas as pd
from typing import Tuple, List, Dict
from src.ml.indices import compute_ffwi_series

def build_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str], Dict]:
    out = df.copy()

    if "wind_kmh" not in out.columns:
        if "wind_ms" in out.columns:
            out["wind_kmh"] = out["wind_ms"] * 3.6
        else:
            raise ValueError("Faltan columnas de viento: ni wind_kmh ni wind_ms están presentes.")

    # ---- features básicas ----
    out["dtr"] = out["tmax_c"] - out["tmin_c"]
    out = out.sort_values("date").reset_index(drop=True)
    out["rain_7d"]  = out["rain_mm"].rolling(7,  min_periods=1).sum()
    out["rain_30d"] = out["rain_mm"].rolling(30, min_periods=1).sum()
    dayofyear = pd.to_datetime(out["date"]).dt.dayofyear.astype(float)
    out["doy_sin"] = np.sin(2*np.pi*dayofyear/365.25)
    out["doy_cos"] = np.cos(2*np.pi*dayofyear/365.25)

    # ---- FFWI ----
    out["ffwi"] = compute_ffwi_series(out["tmean_c"], out["rh_pct"], out["wind_kmh"])

    # ---- etiqueta base: regla adaptativa (percentiles del propio dataset) ----
    # Usar percentiles evita que umbrales absolutos (29°C, 35% RH) nunca se
    # cumplan en climas fríos/húmedos como Tunja (2775 m s.n.m.)
    t_thr  = max(float(out["tmax_c"].quantile(0.80)), 17.0)   # top-20% de tmax
    rh_thr = min(float(out["rh_pct"].quantile(0.25)), 70.0)   # bottom-25% de RH
    w_thr  = max(float(out["wind_kmh"].quantile(0.70)), 7.0)  # top-30% de viento
    rule_soft = (out["tmax_c"] >= t_thr) & (out["rh_pct"] <= rh_thr) & (out["wind_kmh"] >= w_thr)

    N = len(out)
    target_rate = 0.10                  # 10% de positivos deseado
    min_pos = max(int(0.05 * N), 10)    # al menos 5% o 10 días
    base_pos = int(rule_soft.sum())

    add = pd.Series(False, index=out.index)

    def pick_candidates(mask, k):
        # Toma top-k por FFWI entre 'mask'
        idxs = out.loc[mask].sort_values("ffwi", ascending=False).index[:k]
        sel = pd.Series(False, index=out.index); sel.loc[idxs] = True
        return sel

    if base_pos < min_pos:
        # 1) candidatos *secos* estrictos
        ffwi_thr  = max(float(out["ffwi"].quantile(0.90)), 18.0)
        rh_max_ok = 55.0
        wind_min  = 12.0
        r7_max    = 10.0
        r30_max   = 60.0
        tmean_min = 18.0

        neg = ~rule_soft
        cand = (
            neg
            & (out["ffwi"] >= ffwi_thr)
            & (out["rh_pct"] <= rh_max_ok)
            & (out["wind_kmh"] >= wind_min)
            & (out["rain_7d"] <= r7_max)
            & (out["rain_30d"] <= r30_max)
            & (out["tmean_c"] >= tmean_min)
        )
        need = max(min_pos - base_pos, int(target_rate * N) - base_pos)
        add |= pick_candidates(cand, need)

        # 2) si aún falta, relajar progresivamente
        relax_steps = [
            {"rh_max_ok": 60.0},
            {"r7_max": 15.0},
            {"r30_max": float(out["rain_30d"].median())},
            {"tmean_min": 16.0},
            {"wind_min": 8.0},
            {"ffwi_thr": max(float(out["ffwi"].quantile(0.85)), 15.0)},
            {"rh_max_ok": 65.0},
        ]
        for step in relax_steps:
            if (rule_soft | add).sum() >= min_pos:
                break
            # aplicar relajación
            rh_max_ok = step.get("rh_max_ok", rh_max_ok)
            r7_max    = step.get("r7_max", r7_max)
            r30_max   = step.get("r30_max", r30_max)
            tmean_min = step.get("tmean_min", tmean_min)
            wind_min  = step.get("wind_min", wind_min)
            ffwi_thr  = step.get("ffwi_thr", ffwi_thr)

            cand = (
                neg
                & (out["ffwi"] >= ffwi_thr)
                & (out["rh_pct"] <= rh_max_ok)
                & (out["wind_kmh"] >= wind_min)
                & (out["rain_7d"] <= r7_max)
                & (out["rain_30d"] <= r30_max)
                & (out["tmean_c"] >= tmean_min)
                & (~add)   # no repetir
            )
            still_need = min_pos - int((rule_soft | add).sum())
            add |= pick_candidates(cand, still_need)

        # 3) último recurso: top-FFWI global (con RH <= 70)
        if (rule_soft | add).sum() < min_pos:
            cand = (~(rule_soft | add)) & (out["rh_pct"] <= 70.0)
            still_need = min_pos - int((rule_soft | add).sum())
            add |= pick_candidates(cand, still_need)

    out["label_fire"] = (rule_soft | add).astype(int)
    final_rate = float(out["label_fire"].mean())

    feature_cols = [
        "tmax_c","tmin_c","tmean_c","dtr",
        "rh_pct","wind_kmh","rain_mm","rain_7d","rain_30d",
        "doy_sin","doy_cos","ffwi",
    ]

    label_params = {
        "rule_soft": {"tmax_min": t_thr, "rh_max": rh_thr, "wind_min": w_thr},
        "thresholds_type": "adaptive_percentile",
        "final_rate": final_rate,
        "min_pos": int(min_pos),
        "base_pos": int(base_pos),
    }

     # --------- GARANTÍA anti-una-sola-clase ---------
    # si por alguna razón no quedaron positivos, forzamos top-k por sequedad/FFWI
    pos = int(out["label_fire"].sum())
    N = len(out)
    k_min = max(int(0.10 * N), 10)   # al menos 10% o 10 días

    if pos == 0:
        # top por "seco y peligroso"
        score = (
            0.6 * out["ffwi"].fillna(0) +
            0.2 * out["tmax_c"].fillna(0) +
            0.2 * out["wind_kmh"].fillna(0) -
            0.2 * out["rh_pct"].fillna(100) -
            0.1 * out["rain_30d"].fillna(0)
        )
        idxs = score.sort_values(ascending=False).index[:k_min]
        out.loc[idxs, "label_fire"] = 1
        pos = int(out["label_fire"].sum())

    # si por el contrario quedaron casi todos en 1, recorta a 30% máximo
    if pos > 0.30 * N:
        keep = int(0.30 * N)
        idx1 = out.loc[out["label_fire"] == 1].sort_values("ffwi", ascending=False).index[:keep]
        out["label_fire"] = 0
        out.loc[idx1, "label_fire"] = 1

    final_rate = float(out["label_fire"].mean())
    label_params["final_rate"] = final_rate
    return out, feature_cols, label_params
