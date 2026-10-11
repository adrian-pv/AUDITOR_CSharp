"""Catálogo inicial del Módulo 2: Rendimiento (.NET)."""

REGLAS = [
    {
        "codigo": "PERF-001", "nombre": "Variables locales declaradas sin utilización",
        "modulo": "Módulo 2: Rendimiento", "categoria": "Rendimiento (.NET)",
        "tipo_deteccion": "variable_no_usada", "severidad": "ADVERTENCIA",
        "patrones": ["_"], "cwe": "CWE-563",
        "mensaje": "{detalle} Indica código muerto o un cálculo desechado.",
        "recomendacion": "Eliminar la declaración o utilizar el resultado calculado.",
    },
]
