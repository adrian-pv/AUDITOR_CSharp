"""
Orquestador del motor de gobierno y auditoría.

Responsabilidades:
  1. Registrar las reglas activas de los cuatro módulos.
  2. Ejecutar cada regla contra el AST simplificado de cada archivo.
  3. Agregar los hallazgos en las métricas que consume la interfaz
     (LOC total, densidad de errores, score de gobierno, cumplimiento
     por módulo).
"""

from __future__ import annotations

from engine.rule_base import Finding
from modules.gobierno.gov_001_naming_convention import NamingConventionRule
from modules.memoria.mem_004_idisposable_leak import IDisposableLeakRule
from modules.rendimiento.perf_001_unused_variables import UnusedVariablesRule
from modules.seguridad.seg_001_hardcoded_credentials import HardcodedCredentialsRule
from modules.seguridad.seg_002_sql_injection import SqlInjectionRule

# Registro central de reglas. Añadir una regla nueva es agregar una línea aquí.
REGLAS_REGISTRADAS = [
    HardcodedCredentialsRule(),
    SqlInjectionRule(),
    UnusedVariablesRule(),
    IDisposableLeakRule(),
    NamingConventionRule(),
]

MODULOS = [
    "Módulo 1: Seguridad",
    "Módulo 2: Rendimiento",
    "Módulo 3: Memoria",
    "Módulo 4: Gobierno",
]


def run_engine(ast_files: list[dict], reglas: list | None = None) -> dict:
    """
    Ejecuta todas las reglas activas contra la lista de ASTs de archivo y
    retorna el reporte agregado (mismo shape que consume el frontend).
    """
    reglas = reglas if reglas is not None else [r for r in REGLAS_REGISTRADAS if r.activa]

    findings: list[Finding] = []
    for ast_file in ast_files:
        for regla in reglas:
            findings.extend(regla.analyze(ast_file))

    loc_total = sum(f.get("loc", 0) for f in ast_files)
    hallazgos = [_finding_to_dict(f) for f in findings]
    modulos = {r.modulo for r in reglas}
    return {**calcular_metricas(hallazgos, loc_total, modulos), "hallazgos": hallazgos}


PESO_SEVERIDAD = {"CRÍTICO": 12, "ADVERTENCIA": 6, "BAJO": 2}


def calcular_metricas(hallazgos: list[dict], loc_total: int, modulos: set[str] | None = None) -> dict:
    """
    Métricas del panel a partir de una lista de hallazgos ({"modulo", "severidad", ...}).

    `modulos` son los módulos que tienen al menos una regla aplicada: solo esos
    reciben porcentaje de cumplimiento (un módulo sin reglas evaluadas no puede
    marcar 100% por omisión). Se usa tanto al terminar un análisis como cuando el
    auditor elige qué criterios evaluar en un reporte ya generado.
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


def _finding_to_dict(f: Finding) -> dict:
    return {
        "id": f.regla_id,
        "categoria": f.categoria,
        "modulo": f.modulo,
        "severidad": f.severidad.value,
        "archivo": f.archivo,
        "linea": f.linea,
        "descripcion": f.descripcion,
        "recomendacion": f.recomendacion,
        "estado": f.estado.value,
    }
