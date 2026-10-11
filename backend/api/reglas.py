"""
Catálogo de reglas.

  GET   /api/reglas             Todas las reglas (cualquier usuario con sesión).
  GET   /api/reglas/plantillas  Detectores disponibles, categorías OWASP y módulos.
  POST  /api/reglas             Administrador: crea una regla nueva desde una plantilla.
  PUT   /api/reglas/{codigo}    Administrador: actualiza patrones, severidad, textos, OWASP...
  PATCH /api/reglas/{codigo}    Administrador: activa o desactiva la regla.

Ejemplo del caso planteado: si aparece un carácter especial nuevo capaz de
romper una consulta, el Administrador lo agrega a los patrones de SEG-004 y
el siguiente análisis ya lo detecta, sin modificar el código del sistema.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.esquemas import ReglaCambioIn, ReglaIn, ReglaOut
from autenticacion.tokens import requiere_rol, usuario_actual
from engine.detectores import PLANTILLAS
from engine.orchestrator import MODULOS
from engine.owasp import OWASP_2021, OWASP_2025
from engine.regla_def import ReglaDef
from persistencia.database import obtener_sesion
from persistencia.modelos import Regla, Rol, Usuario

router = APIRouter(prefix="/api/reglas", tags=["Reglas"])
solo_admin = requiere_rol(Rol.ADMINISTRADOR)

SEVERIDADES = ["CRÍTICO", "ADVERTENCIA", "BAJO"]
PREFIJOS = {MODULOS[0]: "SEG", MODULOS[1]: "PERF", MODULOS[2]: "MEM", MODULOS[3]: "GOV"}


def regla_a_def(r: Regla) -> ReglaDef:
    return ReglaDef(
        codigo=r.codigo, nombre=r.nombre, modulo=r.modulo, categoria=r.categoria, severidad=r.severidad,
        tipo_deteccion=r.tipo_deteccion or "", patrones=list(r.patrones or []), parametros=dict(r.parametros or {}),
        mensaje=r.mensaje or "{detalle}", recomendacion=r.recomendacion or "", owasp_2021=r.owasp_2021,
        owasp_2025=r.owasp_2025, cwe=r.cwe, activa=r.activa,
    )


@router.get("", response_model=list[ReglaOut])
def listar(_: Usuario = Depends(usuario_actual), sesion: Session = Depends(obtener_sesion)):
    reglas = sesion.scalars(select(Regla)).all()
    orden = {m: i for i, m in enumerate(MODULOS)}
    return sorted(reglas, key=lambda r: (orden.get(r.modulo, 99), r.codigo))


@router.get("/plantillas")
def plantillas(_: Usuario = Depends(usuario_actual)):
    return {
        "detectores": [
            {
                "tipo": tipo,
                "nombre": p["nombre"],
                "descripcion": p["descripcion"],
                "ayuda_patrones": p["ayuda_patrones"],
                "archivos": p["archivos"],
                "parametros": p["parametros"],
                "patrones_opcionales": p.get("patrones_opcionales", False),
            }
            for tipo, p in PLANTILLAS.items()
        ],
        "owasp_2021": OWASP_2021,
        "owasp_2025": OWASP_2025,
        "modulos": MODULOS,
        "severidades": SEVERIDADES,
    }


def _validar(datos: ReglaIn) -> ReglaIn:
    errores = []
    plantilla = PLANTILLAS.get(datos.tipo_deteccion)
    if plantilla is None:
        errores.append(f"Tipo de detección desconocido: {datos.tipo_deteccion}.")
    if datos.modulo not in MODULOS:
        errores.append("Módulo inválido.")
    if datos.severidad not in SEVERIDADES:
        errores.append(f"Severidad inválida. Use: {', '.join(SEVERIDADES)}.")
    if datos.owasp_2021 and datos.owasp_2021 not in OWASP_2021:
        errores.append("Categoría OWASP 2021 inválida.")
    if datos.owasp_2025 and datos.owasp_2025 not in OWASP_2025:
        errores.append("Categoría OWASP 2025 inválida.")

    datos.patrones = list(dict.fromkeys(p for p in datos.patrones if p.strip()))  # sin vacíos ni duplicados
    if plantilla and not datos.patrones and not plantilla.get("patrones_opcionales"):
        errores.append("Agregue al menos un patrón.")
    if datos.tipo_deteccion == "nomenclatura" and datos.patrones:
        try:
            re.compile(datos.patrones[0])
        except re.error as exc:
            errores.append(f"La expresión regular no es válida: {exc}.")
    if datos.tipo_deteccion in ("configuracion_insegura",) and any("=" not in p for p in datos.patrones):
        errores.append("Cada patrón debe tener el formato Clave=valor.")
    if plantilla:
        datos.parametros = {k: v for k, v in datos.parametros.items() if k in plantilla["parametros"]}
    if datos.mensaje and "{" in datos.mensaje.replace("{detalle}", ""):
        errores.append("En el mensaje solo se admite el marcador {detalle}.")
    if errores:
        raise HTTPException(422, " ".join(errores))
    return datos


def _siguiente_codigo(sesion: Session, modulo: str) -> str:
    prefijo = PREFIJOS[modulo]
    usados = [
        int(c.split("-")[1])
        for c in sesion.scalars(select(Regla.codigo).where(Regla.codigo.like(f"{prefijo}-%")))
        if c.split("-")[1].isdigit()
    ]
    return f"{prefijo}-{(max(usados) + 1 if usados else 1):03d}"


def _aplicar(regla: Regla, datos: ReglaIn) -> None:
    for campo in ("nombre", "modulo", "categoria", "severidad", "tipo_deteccion", "patrones", "parametros",
                  "owasp_2021", "owasp_2025", "cwe", "recomendacion", "activa"):
        setattr(regla, campo, getattr(datos, campo))
    regla.mensaje = datos.mensaje or "{detalle}"


@router.post("", response_model=ReglaOut, status_code=status.HTTP_201_CREATED)
def crear(datos: ReglaIn, _: Usuario = Depends(solo_admin), sesion: Session = Depends(obtener_sesion)):
    datos = _validar(datos)
    codigo = datos.codigo or _siguiente_codigo(sesion, datos.modulo)
    if sesion.get(Regla, codigo):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Ya existe una regla con el código {codigo}.")
    regla = Regla(codigo=codigo, predefinida=False)
    _aplicar(regla, datos)
    sesion.add(regla)
    sesion.commit()
    return regla


@router.put("/{codigo}", response_model=ReglaOut)
def actualizar(codigo: str, datos: ReglaIn, _: Usuario = Depends(solo_admin), sesion: Session = Depends(obtener_sesion)):
    regla = sesion.get(Regla, codigo)
    if regla is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Regla no encontrada.")
    datos = _validar(datos)
    if regla.predefinida and datos.tipo_deteccion != regla.tipo_deteccion:
        raise HTTPException(
            422,
            "No se puede cambiar el tipo de detección de una regla predefinida; cree una regla nueva.",
        )
    _aplicar(regla, datos)
    sesion.commit()
    return regla


@router.patch("/{codigo}", response_model=ReglaOut)
def cambiar(
    codigo: str,
    datos: ReglaCambioIn,
    _: Usuario = Depends(solo_admin),
    sesion: Session = Depends(obtener_sesion),
):
    regla = sesion.get(Regla, codigo)
    if regla is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Regla no encontrada.")
    regla.activa = datos.activa
    sesion.commit()
    return regla
