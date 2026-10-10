"""Gestión de usuarios (solo Administrador)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.esquemas import UsuarioCambioIn, UsuarioNuevoIn, UsuarioOut
from autenticacion.contrasenas import hashear
from autenticacion.tokens import requiere_rol
from persistencia.database import obtener_sesion
from persistencia.modelos import Rol, Usuario

router = APIRouter(prefix="/api/usuarios", tags=["Usuarios"])
solo_admin = requiere_rol(Rol.ADMINISTRADOR)


@router.get("", response_model=list[UsuarioOut])
def listar(_: Usuario = Depends(solo_admin), sesion: Session = Depends(obtener_sesion)):
    return sesion.scalars(select(Usuario).order_by(Usuario.id)).all()


@router.post("", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def crear(
    datos: UsuarioNuevoIn,
    _: Usuario = Depends(solo_admin),
    sesion: Session = Depends(obtener_sesion),
):
    correo = datos.correo.strip().lower()
    if sesion.scalar(select(Usuario.id).where(func.lower(Usuario.correo) == correo)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un usuario con ese correo.")
    usuario = Usuario(
        nombre=datos.nombre.strip(),
        correo=correo,
        hash_contrasena=hashear(datos.contrasena),
        rol=datos.rol,
    )
    sesion.add(usuario)
    sesion.commit()
    return usuario


@router.patch("/{usuario_id}", response_model=UsuarioOut)
def modificar(
    usuario_id: int,
    datos: UsuarioCambioIn,
    admin: Usuario = Depends(solo_admin),
    sesion: Session = Depends(obtener_sesion),
):
    usuario = sesion.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")

    pierde_admin = usuario.rol == Rol.ADMINISTRADOR and (
        (datos.rol is not None and datos.rol != Rol.ADMINISTRADOR) or datos.activo is False
    )
    if pierde_admin:
        if usuario.id == admin.id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "No puede quitarse a sí mismo el rol de Administrador ni desactivar su propia cuenta.",
            )
        otros_admins = sesion.scalar(
            select(func.count(Usuario.id)).where(
                Usuario.rol == Rol.ADMINISTRADOR, Usuario.activo.is_(True), Usuario.id != usuario.id
            )
        )
        if not otros_admins:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Debe quedar al menos un Administrador activo.")

    if datos.nombre is not None:
        usuario.nombre = datos.nombre.strip()
    if datos.rol is not None:
        usuario.rol = datos.rol
    if datos.activo is not None:
        usuario.activo = datos.activo
    if datos.contrasena is not None:
        usuario.hash_contrasena = hashear(datos.contrasena)
    sesion.commit()
    return usuario
