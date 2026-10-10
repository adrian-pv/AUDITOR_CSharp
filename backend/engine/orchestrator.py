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
    densidad = round((len(findings) / loc_total) * 100, 2) if loc_total else 0.0

    cumplimiento_por_modulo = _cumplimiento_por_modulo(findings)
    score_gobierno = _score_gobierno(cumplimiento_por_modulo)

    return {
        "stats": {
            "loc_total": loc_total,
            "vulnerabilidades": len(findings),
            "densidad_errores": densidad,
            "score_gobierno": score_gobierno,
        },
        "hallazgos": [_finding_to_dict(f) for f in findings],
        "cumplimiento_por_modulo": cumplimiento_por_modulo,
    }


def _cumplimiento_por_modulo(findings: list[Finding]) -> dict:
    """
    Cumplimiento heurístico por módulo: 100% menos una penalización por
    hallazgo, ponderada por severidad (ver sección 3.4, criterios de
    severidad, del documento).
    """
    peso = {"CRÍTICO": 12, "ADVERTENCIA": 6, "BAJO": 2}
    resultado = {}
    for modulo in MODULOS:
        penalizacion = sum(
            peso.get(f.severidad.value, 4) for f in findings if f.modulo == modulo
        )
        resultado[modulo] = max(0, 100 - penalizacion)
    return resultado


def _score_gobierno(cumplimiento_por_modulo: dict) -> int:
    valores = list(cumplimiento_por_modulo.values())
    return round(sum(valores) / len(valores)) if valores else 100


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
