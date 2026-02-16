import numpy as np
import pandas as pd

def _ffwi_m(temp_c, rh_pct):
    T  = np.clip(np.asarray(temp_c, dtype=float), -50, 60)
    RH = np.clip(np.asarray(rh_pct, dtype=float), 0, 100)
    m = 0.942*(RH**0.679) + 11.0*np.exp((RH-100.0)/10.0) + 0.18*(21.1-T)*(1.0-np.exp(-0.115*RH))
    return np.clip(m, 0.0, 60.0)

def compute_ffwi_series(temp_c, rh_pct, wind_kmh):
    T  = pd.Series(temp_c, dtype="float64")
    RH = pd.Series(rh_pct, dtype="float64")
    Wk = pd.Series(wind_kmh, dtype="float64")
    m   = _ffwi_m(T, RH)
    eta = 1.0 - (2.0*m/100.0) + (m/100.0)**2
    Wmph = Wk * 0.621371
    denom = 0.300 + 0.000714*T + 0.0000036*(T**2)
    ffwi = eta * np.sqrt(1.0 + Wmph**2) / denom
    return pd.Series(np.maximum(0.0, ffwi), index=T.index)

def compute_ffwi_row(temp_c: float, rh_pct: float, wind_kmh: float) -> float:
    m = float(_ffwi_m(temp_c, rh_pct))
    eta = 1.0 - (2.0*m/100.0) + (m/100.0)**2
    Wmph = float(wind_kmh) * 0.621371
    denom = 0.300 + 0.000714*float(temp_c) + 0.0000036*(float(temp_c)**2)
    ffwi = eta * np.sqrt(1.0 + Wmph**2) / denom
    return float(max(0.0, ffwi))
