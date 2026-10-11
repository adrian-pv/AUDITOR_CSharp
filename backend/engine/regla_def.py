"""Definición de una regla tal como la usa el motor (viene de la base de datos o del catálogo)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ReglaDef:
    codigo: str
    nombre: str
    modulo: str
    categoria: str
    severidad: str
    tipo_deteccion: str
    patrones: list[str] = field(default_factory=list)
    parametros: dict = field(default_factory=dict)
    mensaje: str = "{detalle}"
    recomendacion: str = ""
    owasp_2021: str | None = None
    owasp_2025: str | None = None
    cwe: str | None = None
    activa: bool = True

    @classmethod
    def desde_dict(cls, d: dict) -> "ReglaDef":
        campos = cls.__dataclass_fields__
        return cls(**{k: v for k, v in d.items() if k in campos})
