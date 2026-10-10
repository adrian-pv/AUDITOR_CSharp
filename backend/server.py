"""
Servidor local que conecta el frontend con el motor real.

El frontend deja elegir una carpeta de código C# desde el navegador; este
servidor recibe esos archivos, reconstruye la carpeta en un directorio
temporal, corre RoslynBridge + el motor de reglas exactamente igual que
`main.py`, y devuelve el reporte como JSON.

Uso:
    python server.py
    (queda escuchando en http://127.0.0.1:8000; el frontend en desarrollo
    ya está configurado — ver frontend/vite.config.js — para reenviar
    las peticiones a /api hacia este servidor)
"""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from engine.ast_bridge import RoslynBridgeNotBuilt, parse_solution
from engine.orchestrator import run_engine

app = FastAPI(title="Auditor C# — API local")

# Solo el servidor de desarrollo de Vite necesita llamarnos.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CARPETA_REPORTES = Path(__file__).resolve().parent / "reports"


def _nombre_proyecto(archivos: list[UploadFile]) -> str:
    """
    El navegador manda la ruta relativa completa en `filename`
    (p. ej. 'AtuneraPacifico/Controllers/AuthController.cs'), así que el
    primer segmento es el nombre de la carpeta que el usuario eligió.
    """
    for archivo in archivos:
        if archivo.filename and "/" in archivo.filename:
            return archivo.filename.split("/")[0]
    return "solucion"


@app.post("/api/analizar")
async def analizar(archivos: list[UploadFile] = File(...)) -> dict:
    """
    Recibe los archivos .cs seleccionados en el navegador (con su ruta
    relativa preservada en `filename`), los escribe a un directorio
    temporal respetando esa estructura, corre el motor real sobre ellos,
    y guarda el reporte resultante en `backend/reports/`.
    """
    nombre_proyecto = _nombre_proyecto(archivos)

    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp)

        for archivo in archivos:
            if not archivo.filename or not archivo.filename.endswith(".cs"):
                continue
            destino = raiz / archivo.filename
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(await archivo.read())

        try:
            ast_files = parse_solution(raiz)
        except RoslynBridgeNotBuilt as exc:
            return {"error": str(exc)}
        except Exception as exc:  # errores del propio RoslynBridge (código inválido, etc.)
            return {"error": f"No se pudo analizar el código: {exc}"}

    reporte = run_engine(ast_files)
    generado_en = datetime.now(timezone.utc)
    reporte_final = {
        "generado_en": generado_en.isoformat(),
        "proyecto": nombre_proyecto,
        "auditor": "Luis Adrián Pivaral Quiroa",
        **reporte,
    }

    CARPETA_REPORTES.mkdir(exist_ok=True)
    nombre_archivo = f"reporte_{nombre_proyecto}_{generado_en:%Y%m%d_%H%M%S}.json"
    destino_reporte = CARPETA_REPORTES / nombre_archivo
    with open(destino_reporte, "w", encoding="utf-8") as fh:
        json.dump(reporte_final, fh, indent=2, ensure_ascii=False)

    reporte_final["archivo_generado"] = str(destino_reporte)
    return reporte_final


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
