"""
Análisis y reportes.

  POST  /api/analizar            Desarrollador / Administrador: corre el motor y guarda el reporte.
  GET   /api/reportes            Historial (el Desarrollador ve los suyos; Auditor y Admin, todos).
  GET   /api/reportes/{codigo}   Un reporte completo.
  PUT   /api/reportes/{codigo}/criterios
                                 Auditor / Administrador: elige qué reglas (criterios) evaluar
                                 en ese reporte; el panel y el score se recalculan con ellas.
  PATCH /api/hallazgos/{id}      Auditor / Administrador: evalúa un hallazgo (cambia su estado).

El análisis corre por defecto con TODAS las reglas activas del catálogo; el
desarrollador puede quitar algunas antes de analizar (campo `reglas`).
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from api.esquemas import CriteriosIn, EstadoHallazgoIn
from autenticacion.tokens import requiere_rol, usuario_actual
from engine.ast_bridge import RoslynBridgeNotBuilt, parse_solution
from engine.orchestrator import REGLAS_REGISTRADAS, calcular_metricas, run_engine
from engine.rule_base import Estado
from persistencia.database import obtener_sesion
from persistencia.modelos import Hallazgo, Proyecto, Regla, Reporte, ReporteRegla, Rol, Usuario

router = APIRouter(prefix="/api", tags=["Reportes"])

CARPETA_REPORTES = Path(os.environ.get("AUDITOR_REPORTS_DIR", Path(__file__).resolve().parents[1] / "reports"))


# --------------------------------------------------------------------------- utilidades


def _nombre_proyecto(archivos: list[UploadFile]) -> str:
    """El navegador manda la ruta relativa en `filename`; el primer segmento es la carpeta elegida."""
    for archivo in archivos:
        if archivo.filename and "/" in archivo.filename:
            return archivo.filename.split("/")[0]
    return "solucion"


def _ruta_segura(raiz: Path, relativa: str) -> Path | None:
    """Evita que un nombre como '../../x.cs' escriba fuera del directorio temporal."""
    destino = (raiz / relativa).resolve()
    return destino if destino.is_relative_to(raiz.resolve()) else None


def _fecha(r: Reporte) -> str:
    return r.generado_en.replace(tzinfo=r.generado_en.tzinfo or timezone.utc).isoformat()


def _hallazgo_a_dict(h: Hallazgo) -> dict:
    return {
        "hallazgo_id": h.id,
        "id": h.regla_codigo,
        "categoria": h.regla.categoria,
        "modulo": h.regla.modulo,
        "severidad": h.severidad,
        "archivo": h.archivo,
        "linea": h.linea,
        "descripcion": h.descripcion,
        "recomendacion": h.recomendacion,
        "estado": h.estado,
    }


def reporte_a_dict(r: Reporte) -> dict:
    """
    Forma del reporte que consume el frontend y que se guarda como .json.
    Solo lleva ids del usuario y del informe (no datos personales).

    Las métricas y los hallazgos se limitan a los criterios que el auditor dejó
    marcados (`evaluada`). Al generarse el reporte todas las reglas aplicadas
    están marcadas, así que el .json inicial contiene el análisis completo.
    """
    aplicadas = r.reglas_aplicadas
    if aplicadas:
        evaluadas = {a.regla_codigo for a in aplicadas if a.evaluada}
        modulos = {a.regla.modulo for a in aplicadas if a.evaluada}
    else:  # reportes anteriores a esta versión: todas sus reglas cuentan
        evaluadas = {h.regla_codigo for h in r.hallazgos}
        modulos = None

    hallazgos = [_hallazgo_a_dict(h) for h in r.hallazgos if h.regla_codigo in evaluadas]
    metricas = calcular_metricas(hallazgos, r.loc_total, modulos)

    return {
        "reporte_id": r.codigo,
        "usuario_id": r.usuario_id,
        "proyecto": r.proyecto.nombre,
        "generado_en": _fecha(r),
        "stats": metricas["stats"],
        "hallazgos": hallazgos,
        "cumplimiento_por_modulo": metricas["cumplimiento_por_modulo"],
        "criterios": [
            {
                "codigo": a.regla_codigo,
                "nombre": a.regla.nombre,
                "modulo": a.regla.modulo,
                "severidad": a.regla.severidad,
                "evaluada": a.evaluada,
                "hallazgos": sum(1 for h in r.hallazgos if h.regla_codigo == a.regla_codigo),
            }
            for a in sorted(aplicadas, key=lambda a: (a.regla.modulo, a.regla_codigo))
        ],
    }


def _respuesta(r: Reporte) -> dict:
    """Respuesta de la API = reporte + nombre de quien lo generó (solo para mostrar en pantalla)."""
    return {**reporte_a_dict(r), "generado_por": r.usuario.nombre, "archivo_generado": r.archivo_json}


def _puede_ver(usuario: Usuario, reporte: Reporte) -> bool:
    return usuario.rol in (Rol.ADMINISTRADOR, Rol.AUDITOR) or reporte.usuario_id == usuario.id


def _cargar_reporte(sesion: Session, **filtro) -> Reporte | None:
    return sesion.scalar(
        select(Reporte)
        .filter_by(**filtro)
        .options(
            selectinload(Reporte.hallazgos).selectinload(Hallazgo.regla),
            selectinload(Reporte.reglas_aplicadas).selectinload(ReporteRegla.regla),
            selectinload(Reporte.proyecto),
            selectinload(Reporte.usuario),
        )
    )


# --------------------------------------------------------------------------- endpoints


@router.post("/analizar")
async def analizar(
    archivos: list[UploadFile] = File(...),
    reglas: str | None = Form(None, description="Códigos separados por coma; vacío = todas las activas"),
    usuario: Usuario = Depends(requiere_rol(Rol.DESARROLLADOR, Rol.ADMINISTRADOR)),
    sesion: Session = Depends(obtener_sesion),
) -> dict:
    nombre_proyecto = _nombre_proyecto(archivos)

    # Por defecto, todas las reglas activas del catálogo; el desarrollador puede quitar algunas.
    activas = set(sesion.scalars(select(Regla.codigo).where(Regla.activa.is_(True))))
    if reglas:
        pedidas = {c.strip() for c in reglas.split(",") if c.strip()}
        elegidas = activas & pedidas
    else:
        elegidas = activas
    if not elegidas:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Seleccione al menos una regla para analizar.")

    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp)
        for archivo in archivos:
            if not archivo.filename or not archivo.filename.endswith(".cs"):
                continue
            destino = _ruta_segura(raiz, archivo.filename)
            if destino is None:
                continue
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(await archivo.read())

        try:
            ast_files = parse_solution(raiz)
        except RoslynBridgeNotBuilt as exc:
            return {"error": str(exc)}
        except Exception as exc:  # errores del propio RoslynBridge (código inválido, etc.)
            return {"error": f"No se pudo analizar el código: {exc}"}

    resultado = run_engine(ast_files, [r for r in REGLAS_REGISTRADAS if r.id in elegidas])

    proyecto = sesion.scalar(
        select(Proyecto).where(Proyecto.nombre == nombre_proyecto, Proyecto.propietario_id == usuario.id)
    )
    if proyecto is None:
        proyecto = Proyecto(nombre=nombre_proyecto, propietario_id=usuario.id)
        sesion.add(proyecto)
        sesion.flush()

    stats = resultado["stats"]
    reporte = Reporte(
        proyecto_id=proyecto.id,
        usuario_id=usuario.id,
        generado_en=datetime.now(timezone.utc),
        loc_total=stats["loc_total"],
        vulnerabilidades=stats["vulnerabilidades"],
        densidad_errores=stats["densidad_errores"],
        score_gobierno=stats["score_gobierno"],
        cumplimiento_por_modulo=resultado["cumplimiento_por_modulo"],
    )
    reporte.hallazgos = [
        Hallazgo(
            regla_codigo=h["id"],
            severidad=h["severidad"],
            archivo=h["archivo"],
            linea=h["linea"],
            descripcion=h["descripcion"],
            recomendacion=h["recomendacion"],
            estado=h["estado"],
        )
        for h in resultado["hallazgos"]
    ]
    reporte.reglas_aplicadas = [ReporteRegla(regla_codigo=c, evaluada=True) for c in sorted(elegidas)]
    sesion.add(reporte)
    sesion.flush()

    # Copia en disco (historial de archivos, como antes): reporte_<proyecto>_<fecha_hora>.json
    reporte = _cargar_reporte(sesion, id=reporte.id)
    CARPETA_REPORTES.mkdir(exist_ok=True)
    nombre_seguro = re.sub(r'[\\/:*?"<>|]+', "_", nombre_proyecto)
    destino = CARPETA_REPORTES / f"reporte_{nombre_seguro}_{reporte.generado_en:%Y%m%d_%H%M%S}.json"
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(reporte_a_dict(reporte), fh, indent=2, ensure_ascii=False)
    reporte.archivo_json = str(destino)
    sesion.commit()

    return _respuesta(reporte)


@router.get("/reportes")
def historial(usuario: Usuario = Depends(usuario_actual), sesion: Session = Depends(obtener_sesion)):
    consulta = (
        select(Reporte)
        .options(
            selectinload(Reporte.proyecto),
            selectinload(Reporte.usuario),
            selectinload(Reporte.hallazgos).selectinload(Hallazgo.regla),
            selectinload(Reporte.reglas_aplicadas).selectinload(ReporteRegla.regla),
        )
        .order_by(Reporte.generado_en.desc())
    )
    if usuario.rol == Rol.DESARROLLADOR:
        consulta = consulta.where(Reporte.usuario_id == usuario.id)
    resultado = []
    for r in sesion.scalars(consulta):
        datos = reporte_a_dict(r)
        resultado.append(
            {
                "reporte_id": r.codigo,
                "proyecto": r.proyecto.nombre,
                "generado_en": _fecha(r),
                "generado_por": r.usuario.nombre,
                "vulnerabilidades": datos["stats"]["vulnerabilidades"],
                "score_gobierno": datos["stats"]["score_gobierno"],
                "criterios_evaluados": sum(1 for c in datos["criterios"] if c["evaluada"]),
                "criterios_total": len(datos["criterios"]),
            }
        )
    return resultado


@router.get("/reportes/{codigo}")
def detalle(codigo: str, usuario: Usuario = Depends(usuario_actual), sesion: Session = Depends(obtener_sesion)):
    return _respuesta(_reporte_visible(sesion, usuario, codigo))


def _reporte_visible(sesion: Session, usuario: Usuario, codigo: str) -> Reporte:
    try:
        codigo = str(uuid.UUID(codigo))
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reporte no encontrado.")
    reporte = _cargar_reporte(sesion, codigo=codigo)
    if reporte is None or not _puede_ver(usuario, reporte):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reporte no encontrado.")
    return reporte


@router.put("/reportes/{codigo}/criterios")
def elegir_criterios(
    codigo: str,
    datos: CriteriosIn,
    usuario: Usuario = Depends(requiere_rol(Rol.AUDITOR, Rol.ADMINISTRADOR)),
    sesion: Session = Depends(obtener_sesion),
):
    """El auditor marca qué reglas aplicadas en el análisis quiere evaluar."""
    reporte = _reporte_visible(sesion, usuario, codigo)
    aplicadas = {a.regla_codigo: a for a in reporte.reglas_aplicadas}
    pedidas = set(datos.evaluadas)
    if not pedidas:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Seleccione al menos un criterio.")
    ajenas = pedidas - aplicadas.keys()
    if ajenas:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Estas reglas no se aplicaron en el análisis: {', '.join(sorted(ajenas))}.",
        )
    for cod, fila in aplicadas.items():
        fila.evaluada = cod in pedidas
    sesion.commit()
    return _respuesta(_cargar_reporte(sesion, id=reporte.id))


@router.patch("/hallazgos/{hallazgo_id}")
def evaluar_hallazgo(
    hallazgo_id: int,
    datos: EstadoHallazgoIn,
    _: Usuario = Depends(requiere_rol(Rol.AUDITOR, Rol.ADMINISTRADOR)),
    sesion: Session = Depends(obtener_sesion),
):
    validos = [e.value for e in Estado]
    if datos.estado not in validos:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Estado inválido. Use: {', '.join(validos)}.")
    hallazgo = sesion.get(Hallazgo, hallazgo_id)
    if hallazgo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Hallazgo no encontrado.")
    hallazgo.estado = datos.estado
    sesion.commit()
    return {"hallazgo_id": hallazgo.id, "estado": hallazgo.estado}
