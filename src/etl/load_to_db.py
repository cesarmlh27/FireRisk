import os
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from src.utils.paths import DATABASE_URL

CSV_PATH = os.path.join("data", "raw", "Base_de_Datos_Tunja_clima.csv")


def load_csv_to_db(csv_path: str, city: str = "tunja"):
    df = pd.read_csv(csv_path)  # aplica tus limpiezas/renombres como ya lo hacías
    df["city"] = city           # <--- NUEVO
    engine = create_engine(DATABASE_URL, future=True)
    df.to_sql("climatic_data", engine, if_exists="append", index=False)
def doy_to_date(year: int, doy: int):
    return (datetime(int(year), 1, 1) + timedelta(days=int(doy)-1)).date()

def run():
    df = pd.read_csv(CSV_PATH, sep=";", skiprows=18)
    df.columns = [c.strip().upper() for c in df.columns]

    df["date"]     = [doy_to_date(y, d) for y, d in zip(df["YEAR"], df["DOY"])]
    df["tmean_c"]  = df["T2M"].astype(float)
    df["tmax_c"]   = df["T2M_MAX"].astype(float)
    df["tmin_c"]   = df["T2M_MIN"].astype(float)
    df["rh_pct"]   = df["RH2M"].astype(float)
    df["wind_ms"]  = df["WS2M"].astype(float)
    df["rain_mm"]  = df["PRECTOTCORR"].astype(float)

    out = df[["date","YEAR","DOY","tmean_c","tmax_c","tmin_c","rh_pct","wind_ms","rain_mm"]]

    engine = create_engine(DATABASE_URL, future=True)
    with engine.begin() as con:
        for _, r in out.iterrows():
            con.execute(text("""
                INSERT INTO climatic_data (date,year,doy,tmean_c,tmax_c,tmin_c,rh_pct,wind_ms,rain_mm)
                VALUES (:date,:year,:doy,:tmean,:tmax,:tmin,:rh,:wind,:rain)
                ON CONFLICT (date) DO NOTHING;
            """), {
                "date": r["date"], "year": int(r["YEAR"]), "doy": int(r["DOY"]),
                "tmean": float(r["tmean_c"]), "tmax": float(r["tmax_c"]),
                "tmin": float(r["tmin_c"]), "rh": float(r["rh_pct"]),
                "wind": float(r["wind_ms"]), "rain": float(r["rain_mm"])
            })
    print(f"Cargadas {len(out)} filas en climatic_data.")

if __name__ == "__main__":
    run()
