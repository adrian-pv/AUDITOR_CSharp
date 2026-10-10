from engine.rule_base import Rule, Severidad

PALABRAS_CLAVE = ("password", "secret", "apikey", "api_key", "token", "pwd")


class HardcodedCredentialsRule(Rule):
    id = "SEG-001"
    nombre = "Hardcoded Credentials (CWE-259)"
    modulo = "Módulo 1: Seguridad"
    categoria = "Seguridad (OWASP)"
    severidad_defecto = Severidad.CRITICO

    def analyze(self, ast_file: dict) -> list:
        hallazgos = []
        for literal in ast_file.get("literals", []):
            nombre_var = (literal.get("assigned_to") or "").lower()
            if literal.get("kind") == "string" and any(k in nombre_var for k in PALABRAS_CLAVE):
                hallazgos.append(
                    self._finding(
                        archivo=ast_file["file"],
                        linea=literal["line"],
                        descripcion=(
                            f"Se detectó un string asignado a '{literal.get('assigned_to')}' que "
                            "contiene palabras clave de autenticación. Almacenar secretos en texto "
                            "plano vulnera los estándares CWE-259 y OWASP Top 10."
                        ),
                        recomendacion=(
                            "Mover la credencial hacia variables de entorno o "
                            "appsettings.json encriptado."
                        ),
                    )
                )
        return hallazgos
