"""
Clases base compartidas por todas las reglas heurísticas del motor.

Cada módulo (Seguridad, Rendimiento, Memoria, Gobierno) implementa una o más
subclases de `Rule`. El orquestador (`orchestrator.py`) descubre las reglas
registradas, las ejecuta contra el AST simplificado de cada archivo .cs y
recolecta los `Finding` resultantes para construir el reporte final.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severidad(str, Enum):
    CRITICO = "CRÍTICO"
    ADVERTENCIA = "ADVERTENCIA"
    BAJO = "BAJO"


class Estado(str, Enum):
    FALLIDO = "Fallido"
    PENDIENTE = "Pendiente"
    SOLUCIONADO = "Solucionado"


@dataclass(frozen=True)
class Finding:
    """Un hallazgo puntual producido por una regla al analizar un archivo."""

    regla_id: str
    categoria: str
    modulo: str
    severidad: Severidad
    archivo: str
    linea: int
    descripcion: str
    recomendacion: str
    estado: Estado = Estado.PENDIENTE


class Rule:
    """
    Contrato que debe cumplir toda regla heurística.

    Subclases deben definir los atributos de clase (id, nombre, modulo,
    severidad_defecto, categoria) y sobreescribir `analyze`.
    """

    id: str = ""
    nombre: str = ""
    modulo: str = ""
    categoria: str = ""
    severidad_defecto: Severidad = Severidad.ADVERTENCIA
    activa: bool = True

    def analyze(self, ast_file: "dict") -> list[Finding]:
        """
        Recibe el AST simplificado de UN archivo (ver
        `engine/ast_bridge.py` para el esquema) y retorna la lista de
        hallazgos detectados. Debe implementarse en cada subclase.
        """
        raise NotImplementedError

    def _finding(self, archivo: str, linea: int, descripcion: str, recomendacion: str) -> Finding:
        return Finding(
            regla_id=self.id,
            categoria=self.categoria,
            modulo=self.modulo,
            severidad=self.severidad_defecto,
            archivo=archivo,
            linea=linea,
            descripcion=descripcion,
            recomendacion=recomendacion,
        )
