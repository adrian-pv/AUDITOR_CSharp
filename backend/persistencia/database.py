"""
Conexión a la base de datos (PostgreSQL).

La cadena de conexión se toma de la variable AUDITOR_DB_URL, que puede
definirse en el archivo backend/.env (no se sube al repositorio):

    AUDITOR_DB_URL=postgresql://usuario:clave@servidor/neondb?sslmode=require

Si AUDITOR_DB_URL no está definida se usa SQLite (backend/data/auditor.db),
útil solo para pruebas locales sin servidor de base de datos.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

CARPETA_BACKEND = Path(__file__).resolve().parents[1]
CARPETA_DATOS = CARPETA_BACKEND / "data"
URL_SQLITE = f"sqlite:///{(CARPETA_DATOS / 'auditor.db').as_posix()}"


def cargar_env(ruta: Path = CARPETA_BACKEND / ".env") -> None:
    """Lee backend/.env (CLAVE=valor por línea) sin pisar variables ya definidas."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


cargar_env()


class Base(DeclarativeBase):
    pass


def normalizar_url(url: str) -> str:
    """'postgres://' o 'postgresql://' (como las entrega el proveedor) → driver psycopg 3."""
    for prefijo in ("postgres://", "postgresql://"):
        if url.startswith(prefijo):
            return "postgresql+psycopg://" + url[len(prefijo):]
    return url


def descripcion_url(url: str) -> str:
    """Para mostrar en consola sin revelar la contraseña."""
    if url.startswith("sqlite"):
        return "SQLite local (" + url.split("///", 1)[-1] + ")"
    resto = url.split("@", 1)[-1]
    return "PostgreSQL — " + resto.split("?", 1)[0]


def crear_motor(url: str | None = None):
    url = normalizar_url(url or os.environ.get("AUDITOR_DB_URL") or URL_SQLITE)
    if url.startswith("sqlite"):
        if url == URL_SQLITE:
            CARPETA_DATOS.mkdir(exist_ok=True)
        motor = create_engine(url, connect_args={"check_same_thread": False})

        # SQLite no valida llaves foráneas a menos que se active por conexión.
        @event.listens_for(motor, "connect")
        def _activar_fk(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

        return motor

    # pool_pre_ping: un servidor en la nube puede suspenderse por inactividad;
    # así se descartan conexiones muertas antes de usarlas.
    return create_engine(url, pool_pre_ping=True, pool_recycle=300)


motor = crear_motor()
SesionLocal = sessionmaker(bind=motor, autoflush=False, expire_on_commit=False)


def obtener_sesion():
    """Dependencia de FastAPI: una sesión por petición, cerrada al terminar."""
    sesion = SesionLocal()
    try:
        yield sesion
    finally:
        sesion.close()
