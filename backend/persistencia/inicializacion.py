"""
Crea las tablas y carga los datos mínimos la primera vez que arranca el servidor:

  * El catálogo de reglas, tomado de REGLAS_REGISTRADAS del motor (así la
    tabla `reglas` siempre coincide con lo que el motor sabe ejecutar).
  * Un usuario Administrador inicial, solo si la tabla de usuarios está vacía.
    Su contraseña sale de AUDITOR_ADMIN_PASSWORD, o "admin123" si no se define;
    se recomienda cambiarla desde "Mi perfil" al primer ingreso.
"""

from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from autenticacion.contrasenas import hashear
from engine.orchestrator import REGLAS_REGISTRADAS
from persistencia.database import Base
from persistencia.modelos import Regla, Rol, Usuario

ADMIN_CORREO = "admin@auditor.local"


def inicializar(motor, sesion: Session) -> str | None:
    """Retorna la contraseña del admin si se acaba de crear (para mostrarla en consola)."""
    Base.metadata.create_all(motor)

    for regla in REGLAS_REGISTRADAS:
        if sesion.get(Regla, regla.id) is None:
            sesion.add(
                Regla(
                    codigo=regla.id,
                    nombre=regla.nombre,
                    modulo=regla.modulo,
                    categoria=regla.categoria,
                    severidad=regla.severidad_defecto.value,
                    activa=regla.activa,
                )
            )

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
