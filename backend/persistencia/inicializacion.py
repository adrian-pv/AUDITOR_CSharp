"""
Prepara la base de datos al arrancar el servidor:

  1. Crea las tablas que falten.
  2. Migra la tabla `regla` de versiones anteriores agregando las columnas
     nuevas (tipo de detección, patrones, OWASP, CWE...), sin borrar datos.
  3. Copia del catálogo inicial (backend/modules/*/reglas.py) las reglas que
     todavía no existan. Las reglas que el Administrador ya editó NO se
     sobrescriben.
  4. Crea un Administrador inicial si no hay usuarios (contraseña de
     AUDITOR_ADMIN_PASSWORD o "admin123").
"""

from __future__ import annotations

import os

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from autenticacion.contrasenas import hashear
from modules import CATALOGO_INICIAL
from persistencia.database import Base
from persistencia.modelos import Regla, Rol, Usuario

ADMIN_CORREO = "admin@auditor.local"

# Columnas agregadas a `regla` después de la primera versión: nombre → DDL por motor.
COLUMNAS_NUEVAS_REGLA = {
    "tipo_deteccion": ("VARCHAR(40)", "VARCHAR(40)"),
    "patrones": ("JSONB NOT NULL DEFAULT '[]'", "JSON NOT NULL DEFAULT '[]'"),
    "parametros": ("JSONB NOT NULL DEFAULT '{}'", "JSON NOT NULL DEFAULT '{}'"),
    "owasp_2021": ("VARCHAR(10)", "VARCHAR(10)"),
    "owasp_2025": ("VARCHAR(10)", "VARCHAR(10)"),
    "cwe": ("VARCHAR(20)", "VARCHAR(20)"),
    "mensaje": ("TEXT", "TEXT"),
    "recomendacion": ("TEXT", "TEXT"),
    "predefinida": ("BOOLEAN NOT NULL DEFAULT FALSE", "BOOLEAN NOT NULL DEFAULT 0"),
    "fecha_actualizacion": ("TIMESTAMPTZ NOT NULL DEFAULT now()", "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"),
}

CAMPOS_CATALOGO = [
    "nombre", "modulo", "categoria", "severidad", "tipo_deteccion", "patrones", "parametros",
    "owasp_2021", "owasp_2025", "cwe", "mensaje", "recomendacion",
]


def migrar_columnas(motor) -> list[str]:
    existentes = {c["name"] for c in inspect(motor).get_columns("regla")}
    es_pg = motor.dialect.name == "postgresql"
    agregadas = []
    with motor.begin() as conn:
        for nombre, (ddl_pg, ddl_otro) in COLUMNAS_NUEVAS_REGLA.items():
            if nombre not in existentes:
                conn.execute(text(f"ALTER TABLE regla ADD COLUMN {nombre} {ddl_pg if es_pg else ddl_otro}"))
                agregadas.append(nombre)
    return agregadas


def sincronizar_catalogo(sesion: Session) -> None:
    for datos in CATALOGO_INICIAL:
        regla = sesion.get(Regla, datos["codigo"])
        if regla is None:
            regla = Regla(codigo=datos["codigo"], activa=True)
            sesion.add(regla)
        elif regla.tipo_deteccion:  # ya migrada o editada por el Administrador
            continue
        for campo in CAMPOS_CATALOGO:
            valor = datos.get(campo)
            if campo in ("patrones",):
                valor = list(valor or [])
            elif campo == "parametros":
                valor = dict(valor or {})
            setattr(regla, campo, valor)
        regla.predefinida = True


def inicializar(motor, sesion: Session) -> str | None:
    """Retorna la contraseña del admin si se acaba de crear (para mostrarla en consola)."""
    Base.metadata.create_all(motor)
    migrar_columnas(motor)
    sincronizar_catalogo(sesion)

    contrasena_creada = None
    if sesion.scalar(select(Usuario.id).limit(1)) is None:
        contrasena_creada = os.environ.get("AUDITOR_ADMIN_PASSWORD", "admin123")
        sesion.add(
            Usuario(
                nombre="Administrador",
                correo=ADMIN_CORREO,
                hash_contrasena=hashear(contrasena_creada),
                rol=Rol.ADMINISTRADOR,
            )
        )

    sesion.commit()
    return contrasena_creada
