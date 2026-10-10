"""
Configuración compartida de pruebas: cada sesión de pytest usa una base de
datos temporal. Como AUDITOR_DB_URL se define aquí antes de importar la app,
el archivo backend/.env (la base de datos real) nunca se usa en las pruebas.
"""

import os
import sys
import tempfile
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="auditor_test_")
# Por defecto SQLite temporal; para probar contra PostgreSQL defina
# AUDITOR_TEST_DB_URL con una base de datos VACÍA dedicada a pruebas.
os.environ["AUDITOR_DB_URL"] = os.environ.get(
    "AUDITOR_TEST_DB_URL", f"sqlite:///{Path(_TMP, 'test.db').as_posix()}"
)
os.environ["AUDITOR_SECRET"] = "clave-solo-para-pruebas-0123456789abcdef"
os.environ["AUDITOR_REPORTS_DIR"] = str(Path(_TMP, "reports"))
os.environ["AUDITOR_ADMIN_PASSWORD"] = "admin123"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
