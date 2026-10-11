"""Catálogo inicial del Módulo 3: Gestión de Memoria."""

REGLAS = [
    {
        "codigo": "MEM-004", "nombre": "Clases IDisposable sin bloque 'using' o cierre formal",
        "modulo": "Módulo 3: Memoria", "categoria": "Gestión de Memoria",
        "tipo_deteccion": "recurso_sin_liberar", "severidad": "ADVERTENCIA",
        "patrones": ["SqlConnection", "SqlCommand", "SqlDataReader", "FileStream", "StreamReader", "StreamWriter",
                     "HttpClient", "MemoryStream", "Timer", "Process", "BinaryReader", "BinaryWriter"],
        "owasp_2025": "A10:2025", "cwe": "CWE-404",
        "mensaje": "{detalle} El recurso puede quedar abierto y agotar conexiones o memoria.",
        "recomendacion": "Declarar con 'using var' o envolver en un bloque 'using'.",
    },
]
