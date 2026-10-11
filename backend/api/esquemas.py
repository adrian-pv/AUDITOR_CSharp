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
    tipo_deteccion: str | None = None
    patrones: list = []
    parametros: dict = {}
    owasp_2021: str | None = None
    owasp_2025: str | None = None
    cwe: str | None = None
    mensaje: str | None = None
    recomendacion: str | None = None
    predefinida: bool = False
    fecha_actualizacion: datetime | None = None


class ReglaIn(BaseModel):
    """Datos que el Administrador envía al crear o actualizar una regla."""

    codigo: str | None = Field(default=None, max_length=20, pattern=r"^[A-Z]{2,5}-\d{3}$")
    nombre: str = Field(min_length=3, max_length=200)
    modulo: str
    categoria: str = Field(min_length=2, max_length=80)
    severidad: str
    tipo_deteccion: str
    patrones: list[str] = []
    parametros: dict = {}
    owasp_2021: str | None = None
    owasp_2025: str | None = None
    cwe: str | None = Field(default=None, max_length=20)
    mensaje: str | None = Field(default=None, max_length=2000)
    recomendacion: str | None = Field(default=None, max_length=2000)
    activa: bool = True


class ReglaCambioIn(BaseModel):
    activa: bool


class EstadoHallazgoIn(BaseModel):
    estado: str


class CriteriosIn(BaseModel):
    evaluadas: list[str]
