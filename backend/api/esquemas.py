"""Esquemas de entrada/salida de la API (validación con Pydantic)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from persistencia.modelos import Rol


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    correo: str
    rol: Rol
    activo: bool
    creado_en: datetime


class LoginIn(BaseModel):
    correo: str
    contrasena: str


class LoginOut(BaseModel):
    token: str
    usuario: UsuarioOut


class PerfilIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)


class CambioContrasenaIn(BaseModel):
    actual: str
    nueva: str = Field(min_length=8, max_length=128)


class UsuarioNuevoIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    correo: str = Field(min_length=3, max_length=160, pattern=r"^[^@\s]+@[^@\s]+$")
    contrasena: str = Field(min_length=8, max_length=128)
    rol: Rol


class UsuarioCambioIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    rol: Rol | None = None
    activo: bool | None = None
    contrasena: str | None = Field(default=None, min_length=8, max_length=128)


class ReglaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    nombre: str
    modulo: str
    categoria: str
    severidad: str
    activa: bool


class ReglaCambioIn(BaseModel):
    activa: bool


class EstadoHallazgoIn(BaseModel):
    estado: str


class CriteriosIn(BaseModel):
    evaluadas: list[str]
