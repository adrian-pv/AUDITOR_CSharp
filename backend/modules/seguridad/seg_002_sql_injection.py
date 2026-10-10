from engine.rule_base import Rule, Severidad

CONSTRUCTORES_SQL = ("SqlCommand.ctor", "SqlCommand.CommandText")


class SqlInjectionRule(Rule):
    id = "SEG-002"
    nombre = "Inyección SQL - Consultas directas sin parametrizar"
    modulo = "Módulo 1: Seguridad"
    categoria = "Seguridad (OWASP)"
    severidad_defecto = Severidad.CRITICO

    def analyze(self, ast_file: dict) -> list:
        hallazgos = []
        for inv in ast_file.get("invocations", []):
            if inv.get("method") in CONSTRUCTORES_SQL and inv.get("arguments_are_concatenated"):
                hallazgos.append(
                    self._finding(
                        archivo=ast_file["file"],
                        linea=inv["line"],
                        descripcion=(
                            "Se detectó una cadena SQL construida por concatenación directa de "
                            "entrada de usuario (CWE-89, OWASP A03: Injection)."
                        ),
                        recomendacion=(
                            "Reemplazar la concatenación por SqlParameter o un ORM "
                            "parametrizado (p. ej. Entity Framework)."
                        ),
                    )
                )
        return hallazgos
