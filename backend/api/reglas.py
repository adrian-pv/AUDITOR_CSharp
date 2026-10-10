"""Catálogo de reglas: cualquiera lo consulta, solo el Administrador las activa/desactiva."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.esquemas import ReglaCambioIn, ReglaOut
from autenticacion.tokens import requiere_rol, usuario_actual
from persistencia.database import obtener_sesion
from persistencia.modelos import Regla, Rol, Usuario

router = APIRouter(prefix="/api/reglas", tags=["Reglas"])


@router.get("", response_model=list[ReglaOut])
def listar(_: Usuario = Depends(usuario_actual), sesion: Session = Depends(obtener_sesion)):
    return sesion.scalars(select(Regla).order_by(Regla.modulo, Regla.codigo)).all()


@router.patch("/{codigo}", response_model=ReglaOut)
def cambiar(
    codigo: str,
    datos: ReglaCambioIn,
    _: Usuario = Depends(requiere_rol(Rol.ADMINISTRADOR)),
    sesion: Session = Depends(obtener_sesion),
):
    regla = sesion.get(Regla, codigo)
    if regla is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Regla no encontrada.")
    regla.activa = datos.activa
    sesion.commit()
    return regla
