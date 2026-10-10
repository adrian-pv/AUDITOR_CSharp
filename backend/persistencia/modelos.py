"""
Modelo de datos (corresponde al Modelo Entidad-Relación del Capítulo V).

    USUARIO  1 ── N PROYECTO   (registra: el desarrollador dueño del proyecto)
    USUARIO  1 ── N REPORTE    (genera)
    PROYECTO 1 ── N REPORTE    (es analizado en)
    REPORTE  1 ── N HALLAZGO   (contiene)
    REGLA    1 ── N HALLAZGO   (clasifica)
    REPORTE  N ── M REGLA      (aplica; tabla reporte_regla con el atributo `evaluada`)

`reporte_regla` registra qué reglas se ejecutaron en cada análisis (todas por
defecto; el desarrollador puede quitar algunas antes de analizar) y, con
`evaluada`, cuáles de ellas eligió el auditor como criterios al revisar el reporte.

Los nombres de tablas y columnas son los del diagrama (id_usuario,
contrasena_hash, codigo_regla, ...). El atributo de Python puede llamarse
distinto (p. ej. `Usuario.id` ↔ columna `id_usuario`); el script
equivalente en SQL está en backend/sql/esquema_postgresql.sql.

El reporte NO guarda datos personales del usuario: solo `id_usuario` (que
valida que el usuario existe) y un `codigo_reporte` único que, junto con
`fecha_hora`, deja registro de que ese informe se generó con ese usuario.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from persistencia.database import Base

# JSONB en PostgreSQL; JSON genérico en SQLite (pruebas locales).
JSON_BINARIO = JSON().with_variant(JSONB(), "postgresql")


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


class Rol(str, enum.Enum):
    ADMINISTRADOR = "Administrador"
    DESARROLLADOR = "Desarrollador"
    AUDITOR = "Auditor"


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column("id_usuario", Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column("nombre_usuario", String(120))
    correo: Mapped[str] = mapped_column(String(160), unique=True)
    hash_contrasena: Mapped[str] = mapped_column("contrasena_hash", String(255))
    rol: Mapped[Rol] = mapped_column(
        Enum(
            Rol,
            native_enum=False,          # VARCHAR + CHECK, no un tipo ENUM
            create_constraint=True,
            length=20,
            name="ck_usuario_rol",
            values_callable=lambda e: [r.value for r in e],
            validate_strings=True,
        )
    )
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    creado_en: Mapped[datetime] = mapped_column(
        "fecha_creacion", DateTime(timezone=True), default=_ahora, server_default=func.now()
    )

    proyectos: Mapped[list["Proyecto"]] = relationship(back_populates="propietario")
    reportes: Mapped[list["Reporte"]] = relationship(back_populates="usuario")


class Proyecto(Base):
    __tablename__ = "proyecto"
    __table_args__ = (UniqueConstraint("nombre", "id_usuario", name="uq_proyecto_nombre_usuario"),)

    id: Mapped[int] = mapped_column("id_proyecto", Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    propietario_id: Mapped[int] = mapped_column("id_usuario", ForeignKey("usuario.id_usuario"))
    creado_en: Mapped[datetime] = mapped_column(
        "fecha_creacion", DateTime(timezone=True), default=_ahora, server_default=func.now()
    )

    propietario: Mapped[Usuario] = relationship(back_populates="proyectos")
    reportes: Mapped[list["Reporte"]] = relationship(back_populates="proyecto")


class Reporte(Base):
    __tablename__ = "reporte"
    __table_args__ = (
        CheckConstraint("score_gobierno BETWEEN 0 AND 100", name="ck_reporte_score"),
        CheckConstraint("loc_total >= 0 AND vulnerabilidades >= 0", name="ck_reporte_conteos"),
    )

    id: Mapped[int] = mapped_column("id_reporte", Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(
        "codigo_reporte", Uuid(as_uuid=False), unique=True, default=lambda: str(uuid.uuid4())
    )
    usuario_id: Mapped[int] = mapped_column("id_usuario", ForeignKey("usuario.id_usuario"), index=True)
    proyecto_id: Mapped[int] = mapped_column("id_proyecto", ForeignKey("proyecto.id_proyecto"), index=True)
    generado_en: Mapped[datetime] = mapped_column(
        "fecha_hora", DateTime(timezone=True), default=_ahora, server_default=func.now()
    )

    loc_total: Mapped[int] = mapped_column(Integer)
    vulnerabilidades: Mapped[int] = mapped_column(Integer)
    densidad_errores: Mapped[float] = mapped_column(Float)
    score_gobierno: Mapped[int] = mapped_column(SmallInteger)
    cumplimiento_por_modulo: Mapped[dict] = mapped_column("cumplimiento_modulo", JSON_BINARIO)
    archivo_json: Mapped[str | None] = mapped_column(String(500), nullable=True)

    proyecto: Mapped[Proyecto] = relationship(back_populates="reportes")
    usuario: Mapped[Usuario] = relationship(back_populates="reportes")
    hallazgos: Mapped[list["Hallazgo"]] = relationship(
        back_populates="reporte", cascade="all, delete-orphan", order_by="Hallazgo.id"
    )
    reglas_aplicadas: Mapped[list["ReporteRegla"]] = relationship(
        back_populates="reporte", cascade="all, delete-orphan", order_by="ReporteRegla.regla_codigo"
    )


SEVERIDADES = "('CRÍTICO','ADVERTENCIA','BAJO')"


class Regla(Base):
    __tablename__ = "regla"
    __table_args__ = (CheckConstraint(f"severidad IN {SEVERIDADES}", name="ck_regla_severidad"),)

    codigo: Mapped[str] = mapped_column("codigo_regla", String(20), primary_key=True)
    nombre: Mapped[str] = mapped_column("descripcion", String(200))
    modulo: Mapped[str] = mapped_column(String(80))
    categoria: Mapped[str] = mapped_column(String(80))
    severidad: Mapped[str] = mapped_column(String(20))
    activa: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())

    hallazgos: Mapped[list["Hallazgo"]] = relationship(back_populates="regla")


class Hallazgo(Base):
    __tablename__ = "hallazgo"
    __table_args__ = (
        CheckConstraint(f"severidad IN {SEVERIDADES}", name="ck_hallazgo_severidad"),
        CheckConstraint("estado IN ('Pendiente','Solucionado','Fallido')", name="ck_hallazgo_estado"),
        CheckConstraint("linea > 0", name="ck_hallazgo_linea"),
    )

    id: Mapped[int] = mapped_column("id_hallazgo", Integer, primary_key=True)
    reporte_id: Mapped[int] = mapped_column(
        "id_reporte", ForeignKey("reporte.id_reporte", ondelete="CASCADE"), index=True
    )
    regla_codigo: Mapped[str] = mapped_column("codigo_regla", ForeignKey("regla.codigo_regla"), index=True)
    severidad: Mapped[str] = mapped_column(String(20))
    archivo: Mapped[str] = mapped_column(String(500))
    linea: Mapped[int] = mapped_column(Integer)
    descripcion: Mapped[str] = mapped_column(Text)
    recomendacion: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(20), default="Pendiente", server_default="Pendiente")

    reporte: Mapped[Reporte] = relationship(back_populates="hallazgos")
    regla: Mapped[Regla] = relationship(back_populates="hallazgos")


class ReporteRegla(Base):
    """Entidad asociativa REPORTE–REGLA: reglas aplicadas en un análisis y criterios del auditor."""

    __tablename__ = "reporte_regla"

    reporte_id: Mapped[int] = mapped_column(
        "id_reporte", ForeignKey("reporte.id_reporte", ondelete="CASCADE"), primary_key=True
    )
    regla_codigo: Mapped[str] = mapped_column(
        "codigo_regla", ForeignKey("regla.codigo_regla"), primary_key=True
    )
    evaluada: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())

    reporte: Mapped[Reporte] = relationship(back_populates="reglas_aplicadas")
    regla: Mapped[Regla] = relationship()
