from engine.rule_base import Rule, Severidad


class UnusedVariablesRule(Rule):
    id = "PERF-001"
    nombre = "Variables locales declaradas sin utilización en bloque"
    modulo = "Módulo 2: Rendimiento"
    categoria = "Rendimiento (.NET)"
    severidad_defecto = Severidad.ADVERTENCIA

    def analyze(self, ast_file: dict) -> list:
        hallazgos = []
        for decl in ast_file.get("declarations", []):
            if decl.get("kind") == "variable" and decl.get("used") is False:
                hallazgos.append(
                    self._finding(
                        archivo=ast_file["file"],
                        linea=decl["line"],
                        descripcion=(
                            f"La variable local '{decl['name']}' se declara pero nunca se "
                            "vuelve a referenciar dentro de su bloque, lo que indica código "
                            "muerto o un cálculo desechado."
                        ),
                        recomendacion="Eliminar la declaración o utilizar el resultado calculado.",
                    )
                )
        return hallazgos
