# app/auth.py
import hashlib
import hmac
from fastapi import Header, HTTPException
from sqlalchemy import text
from src.db.session import engine


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def require_admin_db(x_api_key: str | None = Header(default=None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Falta X-API-Key")

    candidate_hash = _sha256_hex(x_api_key)

    with engine.connect() as con:
        row = con.execute(text("""
            SELECT role, api_key_sha FROM app_user
            WHERE role = 'admin'
            LIMIT 1
        """)).fetchone()

    # hmac.compare_digest evita timing-attacks al comparar hashes
    if not row or not hmac.compare_digest(row[1], candidate_hash):
        raise HTTPException(status_code=401, detail="No autorizado")

    if row[0] != "admin":
        raise HTTPException(status_code=403, detail="Permisos insuficientes")
