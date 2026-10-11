"""
Catálogo inicial de reglas, organizado por módulo.

Cada módulo define una lista REGLAS (datos, no código): el detector que usa,
sus patrones, severidad, categorías OWASP 2021/2025 y CWE. Al arrancar, el
servidor copia a la base de datos las reglas que todavía no existan; desde
ahí el Administrador las mantiene desde la interfaz.
"""

from modules.gobierno.reglas import REGLAS as _GOB
from modules.memoria.reglas import REGLAS as _MEM
from modules.rendimiento.reglas import REGLAS as _PERF
from modules.seguridad.reglas import REGLAS as _SEG

CATALOGO_INICIAL = [*_SEG, *_PERF, *_MEM, *_GOB]
