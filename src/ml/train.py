# src/ml/train.py
import json, joblib
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score, average_precision_score

from src.ml.features import build_features
from src.utils.paths import DATABASE_URL, MODEL_PATH, FEATURES_PATH


def load_from_db() -> pd.DataFrame:
    engine = create_engine(DATABASE_URL, future=True)
    q = """
      SELECT date, year, doy, tmean_c, tmax_c, tmin_c, rh_pct, wind_ms, wind_kmh, rain_mm
      FROM climatic_data
      ORDER BY date
    """
    with engine.connect() as con:
        df = pd.read_sql(text(q), con)
    return df


def train_and_save():
    df = load_from_db()
    df, feature_cols, label_params = build_features(df)

    # Orden y limpieza de filas con NaN en features o en la etiqueta
    df = df.sort_values("date").reset_index(drop=True)
    before = len(df)
    df = df.dropna(subset=feature_cols + ["label_fire"]).reset_index(drop=True)
    dropped = before - len(df)

    # Split (80/20) con salvaguarda para series cortas
    cut = int(len(df) * 0.8) if len(df) > 20 else max(len(df) - 5, 1)
    train_df = df.iloc[:cut]
    valid_df = df.iloc[cut:] if cut < len(df) else df.iloc[0:0]

    X_train = train_df[feature_cols].to_numpy()
    y_train = train_df["label_fire"].to_numpy().astype(int)
    if len(valid_df) == 0:
        valid_df = train_df.copy()
    X_valid = valid_df[feature_cols].to_numpy()
    y_valid = valid_df["label_fire"].to_numpy().astype(int)

    classes = np.unique(y_train)
    single_class = (len(classes) < 2)

    base = RandomForestClassifier(
        n_estimators=500,
        min_samples_leaf=2,
        n_jobs=-1,
        random_state=42,
        class_weight=(None if single_class else "balanced"),
    )

    if single_class:
        clf = base.fit(X_train, y_train)
        calibrated = False
    else:
        # <-- cambio clave: 'sigmoid' en lugar de 'isotonic'
        clf = CalibratedClassifierCV(base, method="sigmoid", cv=3).fit(X_train, y_train)
        calibrated = True

    # Métricas (pueden quedar NaN si valid tiene 1 clase)
    try:
        has_two = len(np.unique(getattr(clf, "classes_", [0, 1]))) > 1
        p_valid = clf.predict_proba(X_valid)[:, 1] if has_two else np.zeros(len(X_valid))
        if len(np.unique(y_valid)) > 1 and len(p_valid) > 0:
            auc = roc_auc_score(y_valid, p_valid)
            ap = average_precision_score(y_valid, p_valid)
        else:
            auc = float("nan")
            ap = float("nan")
    except Exception:
        auc = float("nan")
        ap = float("nan")

    # Guardar modelo y features
    joblib.dump(clf, MODEL_PATH)
    with open(FEATURES_PATH, "w", encoding="utf-8") as f:
        json.dump({"feature_cols": feature_cols}, f, ensure_ascii=False, indent=2)

    # Metadatos para auditoría
    def _safe(x):
        try:
            x = float(x)
            return x if np.isfinite(x) else None
        except Exception:
            return None

    min_str = pd.to_datetime(df["date"]).min().strftime("%Y-%m-%d")
    max_str = pd.to_datetime(df["date"]).max().strftime("%Y-%m-%d")

    meta = {
        "rows": int(len(df)),
        "dropped_rows_due_to_nan": int(dropped),
        "date_range": [min_str, max_str],
        "labeling": label_params,
        "class_balance_train": {int(c): int((y_train == c).sum()) for c in np.unique(y_train)},
        "features": feature_cols,
        "calibrated": calibrated,
        "auc": _safe(auc),
        "ap": _safe(ap),
    }
    with open("models/metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return meta


if __name__ == "__main__":
    print(train_and_save())
