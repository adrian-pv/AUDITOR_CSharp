import re

from engine.rule_base import Rule, Severidad

PASCAL_CASE = re.compile(r"^[A-Z][a-zA-Z0-9]*$")


class NamingConventionRule(Rule):
    id = "GOV-001"
    nombre = "Falta de nomenclatura estándar CamelCase / PascalCase"
    modulo = "Módulo 4: Gobierno"
    categoria = "Gobierno Estructural"
    severidad_defecto = Severidad.BAJO

    def analyze(self, ast_file: dict) -> list:
        hallazgos = []
        for decl in ast_file.get("declarations", []):
            if decl.get("kind") == "property" and "public" in decl.get("modifiers", []):
                if not PASCAL_CASE.match(decl["name"]):
                    hallazgos.append(
                        self._finding(
                            archivo=ast_file["file"],
                            linea=decl["line"],
                            descripcion=(
                                f"La propiedad pública '{decl['name']}' no sigue la convención "
                                "PascalCase establecida por las guías de estilo de .NET."
                            ),
                            recomendacion="Renombrar siguiendo PascalCase (p. ej. 'UserName').",
                        )
                    )
        return hallazgos
