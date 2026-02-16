# app/auth.py
import hashlib
from fastapi import Header, HTTPException
from sqlalchemy import create_engine, text
from src.utils.paths import DATABASE_URL

def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def require_admin_db(x_api_key: str | None = Header(default=None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Falta X-API-Key")
    engine = create_engine(DATABASE_URL, future=True)
    with engine.connect() as con:
        row = con.execute(text("""
            SELECT role FROM app_user
            WHERE api_key_sha = :h
            LIMIT 1
        """), {"h": _sha256_hex(x_api_key)}).fetchone()
    if not row or row[0] != "admin":
        raise HTTPException(status_code=401, detail="No autorizado")
    