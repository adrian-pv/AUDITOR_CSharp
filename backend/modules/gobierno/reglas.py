"""Catálogo inicial del Módulo 4: Gobierno Estructural."""

REGLAS = [
    {
        "codigo": "GOV-001", "nombre": "Falta de nomenclatura estándar PascalCase",
        "modulo": "Módulo 4: Gobierno", "categoria": "Gobierno Estructural",
        "tipo_deteccion": "nomenclatura", "severidad": "BAJO",
        "patrones": ["^[A-Z][a-zA-Z0-9]*$"],
        "parametros": {"tipos": ["property"], "modificador": "public"},
        "mensaje": "{detalle} Las guías de estilo de .NET usan PascalCase para miembros públicos.",
        "recomendacion": "Renombrar siguiendo PascalCase (p. ej. 'UserName').",
    },
]
