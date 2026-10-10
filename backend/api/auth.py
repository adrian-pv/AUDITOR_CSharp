"""Inicio de sesión y perfil del usuario que tiene la sesión abierta."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.esquemas import CambioContrasenaIn, LoginIn, LoginOut, PerfilIn, UsuarioOut
from autenticacion.contrasenas import hashear, verificar
from autenticacion.tokens import crear_token, usuario_actual
from persistencia.database import obtener_sesion
from persistencia.modelos import Usuario

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


@router.post("/login", response_model=LoginOut)
def login(datos: LoginIn, sesion: Session = Depends(obtener_sesion)):
    usuario = sesion.scalar(
        select(Usuario).where(func.lower(Usuario.correo) == datos.correo.strip().lower())
    )
    # Mismo mensaje para "no existe" y "contraseña incorrecta": no revela qué correos existen.
    if usuario is None or not verificar(datos.contrasena, usuario.hash_contrasena):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Correo o contraseña incorrectos.")
    if not usuario.activo:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Su cuenta está desactivada. Contacte al administrador.")
    return LoginOut(token=crear_token(usuario), usuario=UsuarioOut.model_validate(usuario))


@router.get("/yo", response_model=UsuarioOut)
def yo(usuario: Usuario = Depends(usuario_actual)):
    return usuario


@router.patch("/yo", response_model=UsuarioOut)
def actualizar_perfil(
    datos: PerfilIn,
    usuario: Usuario = Depends(usuario_actual),
    sesion: Session = Depends(obtener_sesion),
):
    usuario = sesion.merge(usuario)
    usuario.nombre = datos.nombre.strip()
    sesion.commit()
    return usuario


@router.post("/yo/contrasena", status_code=status.HTTP_204_NO_CONTENT)
def cambiar_contrasena(
    datos: CambioContrasenaIn,
    usuario: Usuario = Depends(usuario_actual),
    sesion: Session = Depends(obtener_sesion),
):
    if not verificar(datos.actual, usuario.hash_contrasena):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La contraseña actual no es correcta.")
    usuario = sesion.merge(usuario)
    usuario.hash_contrasena = hashear(datos.nueva)
    sesion.commit()
