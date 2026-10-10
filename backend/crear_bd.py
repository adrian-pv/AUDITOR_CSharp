"""
Crea las tablas de AUDITOR_C# en la base de datos PostgreSQL configurada en
backend/.env (AUDITOR_DB_URL), ejecutando sql/esquema_postgresql.sql.

Uso:
    python crear_bd.py

Si algunas tablas ya existen, solo crea las que falten (no borra ni modifica datos).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from persistencia.database import cargar_env  # noqa: E402

TABLAS = ["usuario", "proyecto", "regla", "reporte", "hallazgo", "reporte_regla"]
SCRIPT = Path(__file__).resolve().parent / "sql" / "esquema_postgresql.sql"


def main() -> None:
    cargar_env()
    url = os.environ.get("AUDITOR_DB_URL", "")
    if not url.startswith(("postgres://", "postgresql://")):
        sys.exit(
            "No hay una cadena de conexión de PostgreSQL en backend/.env.\n"
            "Copie .env.example como .env y complete AUDITOR_DB_URL=postgresql://..."
        )

    import psycopg

    with psycopg.connect(url, autocommit=True) as conn:
        servidor = conn.info.host
        antes = {
            r[0]
            for r in conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
        }
        # El script es idempotente: solo crea lo que falte y nunca borra datos.
        conn.execute(SCRIPT.read_text(encoding="utf-8"))
        nuevas = [t for t in TABLAS if t not in antes]
        if nuevas:
            print(f"Tablas creadas en {servidor}: {', '.join(nuevas)}")
        else:
            print(f"Todas las tablas ya existían en {servidor}; no se hizo ningún cambio.")

        for tabla in TABLAS:
            n = conn.execute(f"SELECT count(*) FROM {tabla}").fetchone()[0]
            print(f"  {tabla:<14} {n} fila(s)")


if __name__ == "__main__":
    main()
