"""
Servidor local de AUDITOR_C#: API con inicio de sesión, base de datos y motor real.

Uso:
    python server.py
    (queda escuchando en http://127.0.0.1:8000; el frontend en desarrollo
    reenvía las peticiones a /api hacia este servidor — ver frontend/vite.config.js)

La conexión a PostgreSQL se configura en backend/.env (ver .env.example).
La primera vez crea las tablas que falten, carga el catálogo de reglas y
crea un Administrador inicial (ver persistencia/inicializacion.py).
Documentación interactiva de la API: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import auth, reglas, reportes, usuarios
from persistencia.database import SesionLocal, descripcion_url, motor
from persistencia.inicializacion import ADMIN_CORREO, inicializar


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    print(f"  Base de datos: {descripcion_url(motor.url.render_as_string(hide_password=True))}")
    with SesionLocal() as sesion:
        contrasena = inicializar(motor, sesion)
    if contrasena:
        print("\n  Usuario administrador inicial creado:")
        print(f"    correo:     {ADMIN_CORREO}")
        print(f"    contraseña: {contrasena}")
        print("  Cámbiela desde 'Mi perfil' después de iniciar sesión.\n")
    yield


app = FastAPI(title="AUDITOR_C# — API local", lifespan=ciclo_de_vida)

# Solo el servidor de desarrollo de Vite necesita llamarnos.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(reglas.router)
app.include_router(reportes.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
