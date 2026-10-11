"""
Formato del reporte como archivo .json (descargar / cargar).

El archivo lleva TODOS los hallazgos del análisis con su estado y la lista de
criterios (reglas aplicadas) indicando cuáles evaluó el auditor. Así, quien lo
cargue después puede volver a elegir criterios y las métricas se recalculan
igual que con un reporte guardado.

Un archivo cargado viene de un tercero y no es confiable: se valida con
Pydantic (tipos, longitudes, valores permitidos) y las métricas NUNCA se toman
del archivo, siempre se recalculan a partir de sus hallazgos. Nada de lo que se
carga se guarda en la base de datos.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from engine.orchestrator import calcular_metricas
from persistencia.modelos import ESTADOS_HALLAZGO

FORMATO = "AUDITOR_CSharp/reporte"
VERSION = 1
SEVERIDADES = ("CRÍTICO", "ADVERTENCIA", "BAJO")

Texto = Field(default="", max_length=4000)


class HallazgoArchivo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1, max_length=20, description="Código de la regla, p. ej. SEG-004")
    categoria: str = Field(default="", max_length=120)
    modulo: str = Field(min_length=1, max_length=60)
    severidad: Literal[SEVERIDADES]  # type: ignore[valid-type]
    archivo: str = Field(min_length=1, max_length=500)
    linea: int = Field(ge=0, le=10_000_000)
    descripcion: str = Texto
    recomendacion: str = Texto
    estado: str = Field(default="Pendiente", max_length=30)
    owasp_2021: str | None = Field(default=None, max_length=20)
    owasp_2025: str | None = Field(default=None, max_length=20)
    cwe: str | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def _estado_valido(self):
        if self.estado not in ESTADOS_HALLAZGO:
            raise ValueError(f"estado '{self.estado}' no es válido (use: {', '.join(ESTADOS_HALLAZGO)})")
        return self


class CriterioArchivo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    codigo: str = Field(min_length=1, max_length=20)
    nombre: str = Field(default="", max_length=200)
    modulo: str = Field(min_length=1, max_length=60)
    severidad: Literal[SEVERIDADES]  # type: ignore[valid-type]
    evaluada: bool = True


class StatsArchivo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    loc_total: int = Field(default=0, ge=0, le=100_000_000)


class ReporteArchivo(BaseModel):
    """
    Archivo .json de un reporte. También acepta los .json que el sistema
    guardaba en la carpeta `reports/` antes de existir este formato (sin
    `formato` ni `loc_total`): en ese caso se toman de `stats` y, si no trae
    criterios, se deducen de los hallazgos.
    """

    model_config = ConfigDict(extra="ignore")

    formato: str | None = None
    version: int | None = None
    reporte_id: str | None = Field(default=None, max_length=60)
    proyecto: str = Field(min_length=1, max_length=200)
    generado_en: str | None = Field(default=None, max_length=40)
    loc_total: int | None = Field(default=None, ge=0, le=100_000_000)
    stats: StatsArchivo | None = None
    criterios: list[CriterioArchivo] = Field(default_factory=list, max_length=1000)
    hallazgos: list[HallazgoArchivo] = Field(default_factory=list, max_length=50_000)

    @model_validator(mode="after")
    def _coherente(self):
        if self.formato is not None and self.formato != FORMATO:
            raise ValueError(f"El archivo no es un reporte de AUDITOR_C# (formato '{self.formato}').")
        if self.version is not None and self.version > VERSION:
            raise ValueError(
                f"El reporte usa la versión {self.version} del formato; esta versión del sistema lee hasta la {VERSION}."
            )
        if self.loc_total is None:
            self.loc_total = self.stats.loc_total if self.stats else 0

        if not self.criterios:  # archivo antiguo: un criterio por regla con hallazgos
            vistos: dict[str, CriterioArchivo] = {}
            for h in self.hallazgos:
                vistos.setdefault(h.id, CriterioArchivo(codigo=h.id, modulo=h.modulo, severidad=h.severidad))
            self.criterios = list(vistos.values())

        codigos = [c.codigo for c in self.criterios]
        if len(codigos) != len(set(codigos)):
            raise ValueError("Hay criterios repetidos en el archivo.")
        sin_criterio = sorted({h.id for h in self.hallazgos} - set(codigos))
        if sin_criterio:
            raise ValueError(f"Hay hallazgos de reglas que no están en 'criterios': {', '.join(sin_criterio)}.")
        return self


def documento_a_vista(doc: ReporteArchivo) -> dict:
    """
    Convierte un archivo validado en la misma forma que usa el frontend para un
    reporte guardado. Las métricas se recalculan con los criterios evaluados.
    `hallazgo_id` es la posición del hallazgo dentro del archivo (no un id de BD).
    """
    evaluadas = {c.codigo for c in doc.criterios if c.evaluada}
    modulos = {c.modulo for c in doc.criterios if c.evaluada}
    hallazgos = [
        {"hallazgo_id": i, **h.model_dump()} for i, h in enumerate(doc.hallazgos) if h.id in evaluadas
    ]
    metricas = calcular_metricas(hallazgos, doc.loc_total or 0, modulos)
    conteo: dict[str, int] = {}
    for h in doc.hallazgos:
        conteo[h.id] = conteo.get(h.id, 0) + 1

    return {
        "importado": True,
        "reporte_id": doc.reporte_id,
        "proyecto": doc.proyecto,
        "generado_en": doc.generado_en,
        "stats": metricas["stats"],
        "hallazgos": hallazgos,
        "cumplimiento_por_modulo": metricas["cumplimiento_por_modulo"],
        "criterios": [
            {**c.model_dump(), "hallazgos": conteo.get(c.codigo, 0)}
            for c in sorted(doc.criterios, key=lambda c: (c.modulo, c.codigo))
        ],
        # El archivo normalizado: el frontend lo conserva para volver a descargarlo
        # con los cambios del auditor (criterios y estados).
        "documento": {**doc.model_dump(exclude={"stats"}), "formato": FORMATO, "version": VERSION},
    }
