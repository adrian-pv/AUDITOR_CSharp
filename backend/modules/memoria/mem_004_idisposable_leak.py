from engine.rule_base import Rule, Severidad


class IDisposableLeakRule(Rule):
    id = "MEM-004"
    nombre = "Clases IDisposable sin bloque 'using' o cierre formal"
    modulo = "Módulo 3: Memoria"
    categoria = "Gestión de Memoria"
    severidad_defecto = Severidad.ADVERTENCIA

    def analyze(self, ast_file: dict) -> list:
        hallazgos = []
        for disp in ast_file.get("disposables", []):
            if not disp.get("wrapped_in_using") and not disp.get("disposed_explicitly"):
                hallazgos.append(
                    self._finding(
                        archivo=ast_file["file"],
                        linea=disp["line"],
                        descripcion=(
                            f"'{disp['variable']}' de tipo {disp['type']} implementa IDisposable "
                            "pero ningún camino del flujo de control invoca Dispose() ni usa el "
                            "bloque 'using'."
                        ),
                        recomendacion=(
                            "Envolver la instancia en un bloque 'using' o declarar "
                            "'using var' en su creación."
                        ),
                    )
                )
        return hallazgos
