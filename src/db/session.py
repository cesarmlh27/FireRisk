# src/db/session.py
"""Motor y SessionFactory compartidos para toda la aplicación.

Importa `engine` en lugar de llamar create_engine() en cada módulo/endpoint,
para no abrir un pool de conexiones nuevo por petición.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.utils.paths import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,          # descarta conexiones rotas automáticamente
)

SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_session() -> Session:
    """Devuelve una nueva sesión de BD. Usar con 'with get_session() as s:'."""
    return SessionFactory()
