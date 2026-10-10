"""
Sesiones con JWT (JSON Web Token).

Al iniciar sesión el servidor firma un token con el id del usuario y su rol;
el frontend lo envía en cada petición (`Authorization: Bearer <token>`).

La clave de firma sale de AUDITOR_SECRET; si no está definida se genera una
al azar la primera vez y se guarda en backend/data/.secret, para que las
sesiones sigan siendo válidas tras reiniciar el servidor.
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from persistencia.database import CARPETA_DATOS, obtener_sesion
from persistencia.modelos import Rol, Usuario

ALGORITMO = "HS256"
DURACION = timedelta(hours=8)


def _clave_secreta() -> str:
    if os.environ.get("AUDITOR_SECRET"):
        return os.environ["AUDITOR_SECRET"]
    ruta = CARPETA_DATOS / ".secret"
    if ruta.exists():
        return ruta.read_text().strip()
    CARPETA_DATOS.mkdir(exist_ok=True)
    clave = secrets.token_hex(32)
    ruta.write_text(clave)
    return clave


CLAVE = _clave_secreta()
_bearer = HTTPBearer(auto_error=False)


def crear_token(usuario: Usuario) -> str:
    ahora = datetime.now(timezone.utc)
    datos = {"sub": str(usuario.id), "rol": usuario.rol.value, "iat": ahora, "exp": ahora + DURACION}
    return jwt.encode(datos, CLAVE, algorithm=ALGORITMO)


def usuario_actual(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    sesion: Session = Depends(obtener_sesion),
) -> Usuario:
    no_autorizado = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesión inválida o expirada. Inicie sesión de nuevo.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if cred is None:
        raise no_autorizado
    try:
        datos = jwt.decode(cred.credentials, CLAVE, algorithms=[ALGORITMO])
        usuario_id = int(datos["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise no_autorizado

    usuario = sesion.get(Usuario, usuario_id)
    if usuario is None or not usuario.activo:
        raise no_autorizado
    return usuario


def requiere_rol(*roles: Rol):
    """Dependencia que deja pasar solo a los roles indicados."""

    def _verificar(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Esta acción requiere el rol: {', '.join(r.value for r in roles)}.",
            )
        return usuario

    return _verificar
