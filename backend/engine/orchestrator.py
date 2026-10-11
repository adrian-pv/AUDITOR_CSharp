"""
Orquestador del motor de gobierno y auditoría.

Responsabilidades:
  1. Recibir las reglas a aplicar (definiciones de la base de datos o, sin
     base de datos, el catálogo inicial de modules/).
  2. Ejecutar el detector de cada regla contra el AST de cada archivo.
  3. Agregar los hallazgos en las métricas que consume la interfaz (LOC,
     densidad de errores, score de gobierno y cumplimiento por módulo).
"""

from __future__ import annotations

from engine.detectores import DETECTORES, aplica_a
from engine.regla_def import ReglaDef
from modules import CATALOGO_INICIAL

MODULOS = [
    "Módulo 1: Seguridad",
    "Módulo 2: Rendimiento",
    "Módulo 3: Memoria",
    "Módulo 4: Gobierno",
]


def reglas_del_catalogo() -> list[ReglaDef]:
    return [ReglaDef.desde_dict(r) for r in CATALOGO_INICIAL]


def run_engine(ast_files: list[dict], reglas: list[ReglaDef] | None = None) -> dict:
    """Ejecuta las reglas contra los ASTs y retorna el reporte agregado."""
    reglas = reglas if reglas is not None else [r for r in reglas_del_catalogo() if r.activa]

    hallazgos: list[dict] = []
    for ast_file in ast_files:
        for regla in reglas:
            detector = DETECTORES.get(regla.tipo_deteccion)
            if detector is None or not aplica_a(regla.tipo_deteccion, ast_file):
                continue
            vistos = set()
            for linea, detalle in detector(regla, ast_file):
                if (linea, detalle) in vistos:
                    continue
                vistos.add((linea, detalle))
                hallazgos.append(_hallazgo(regla, ast_file["file"], linea, detalle))

    # Las métricas de LOC cuentan solo código C# (no .csproj ni appsettings).
    loc_total = sum(f.get("loc", 0) for f in ast_files if f.get("kind", "csharp") == "csharp")
    modulos = {r.modulo for r in reglas}
    return {**calcular_metricas(hallazgos, loc_total, modulos), "hallazgos": hallazgos}


def _hallazgo(regla: ReglaDef, archivo: str, linea: int, detalle: str) -> dict:
    try:
        descripcion = (regla.mensaje or "{detalle}").format(detalle=detalle)
    except (KeyError, IndexError, ValueError):  # plantilla mal escrita por el usuario
        descripcion = f"{detalle} {regla.mensaje}"
    return {
        "id": regla.codigo,
        "categoria": regla.categoria,
        "modulo": regla.modulo,
        "severidad": regla.severidad,
        "archivo": archivo,
        "linea": max(1, int(linea)),
        "descripcion": descripcion.strip(),
        "recomendacion": regla.recomendacion,
        "estado": "Pendiente",
        "owasp_2021": regla.owasp_2021,
        "owasp_2025": regla.owasp_2025,
        "cwe": regla.cwe,
    }


PESO_SEVERIDAD = {"CRÍTICO": 12, "ADVERTENCIA": 6, "BAJO": 2}


def calcular_metricas(hallazgos: list[dict], loc_total: int, modulos: set[str] | None = None) -> dict:
    """
    Métricas del panel a partir de una lista de hallazgos ({"modulo", "severidad", ...}).

    `modulos` son los módulos que tienen al menos una regla aplicada: solo esos
    reciben porcentaje de cumplimiento. Se usa al terminar un análisis y cuando
    el auditor elige qué criterios evaluar en un reporte ya generado.
    """
    modulos = set(MODULOS) if modulos is None else modulos
    densidad = round((len(hallazgos) / loc_total) * 100, 2) if loc_total else 0.0

    # Cumplimiento heurístico por módulo: 100% menos una penalización por
    # hallazgo, ponderada por severidad (sección 3.4, criterios de severidad).
    cumplimiento = {}
    for modulo in MODULOS:
        if modulo not in modulos:
            continue
        penalizacion = sum(PESO_SEVERIDAD.get(h["severidad"], 4) for h in hallazgos if h["modulo"] == modulo)
        cumplimiento[modulo] = max(0, 100 - penalizacion)

    valores = list(cumplimiento.values())
    score = round(sum(valores) / len(valores)) if valores else 100

    return {
        "stats": {
            "loc_total": loc_total,
            "vulnerabilidades": len(hallazgos),
            "densidad_errores": densidad,
            "score_gobierno": score,
        },
        "cumplimiento_por_modulo": cumplimiento,
    }
