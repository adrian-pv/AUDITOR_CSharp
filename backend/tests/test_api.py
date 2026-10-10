"""Pruebas de la API: inicio de sesión, roles, análisis guardado en BD e historial."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.reportes
import server
from engine.ast_bridge import load_ast_fixture
from persistencia.inicializacion import ADMIN_CORREO

FIXTURE = Path(__file__).parent / "fixtures" / "atunerapacifico_ast.json"


@pytest.fixture(scope="module")
def cliente():
    with TestClient(server.app) as c:  # el 'with' dispara la creación de la BD
        yield c


@pytest.fixture(autouse=True)
def motor_simulado(monkeypatch):
    """Sustituye RoslynBridge por el AST de ejemplo (no requiere .NET en las pruebas)."""
    monkeypatch.setattr(api.reportes, "parse_solution", lambda _ruta: load_ast_fixture(FIXTURE))


def _login(cliente, correo, contrasena):
    r = cliente.post("/api/auth/login", json={"correo": correo, "contrasena": contrasena})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _crear(cliente, admin, correo, rol):
    r = cliente.post(
        "/api/usuarios",
        headers=admin,
        json={"nombre": correo.split("@")[0].title(), "correo": correo, "contrasena": "clave-segura", "rol": rol},
    )
    assert r.status_code in (201, 409), r.text
    return _login(cliente, correo, "clave-segura")


def _analizar(cliente, headers, reglas=None):
    archivos = [("archivos", ("AtuneraPacifico/Controllers/AuthController.cs", b"class A {}", "text/plain"))]
    data = {"reglas": ",".join(reglas)} if reglas is not None else None
    return cliente.post("/api/analizar", headers=headers, files=archivos, data=data)


def test_login_incorrecto_no_revela_si_el_correo_existe(cliente):
    a = cliente.post("/api/auth/login", json={"correo": ADMIN_CORREO, "contrasena": "mala"})
    b = cliente.post("/api/auth/login", json={"correo": "nadie@x.com", "contrasena": "mala"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_sin_token_no_hay_acceso(cliente):
    assert cliente.get("/api/reportes").status_code == 401
    assert cliente.get("/api/auth/yo", headers={"Authorization": "Bearer basura"}).status_code == 401


def test_admin_inicial_y_perfil(cliente):
    admin = _login(cliente, ADMIN_CORREO, "admin123")
    yo = cliente.get("/api/auth/yo", headers=admin).json()
    assert yo["rol"] == "Administrador"
    assert "hash_contrasena" not in yo


def test_solo_admin_gestiona_usuarios(cliente):
    admin = _login(cliente, ADMIN_CORREO, "admin123")
    dev = _crear(cliente, admin, "dev1@test.com", "Desarrollador")
    assert cliente.get("/api/usuarios", headers=dev).status_code == 403
    assert cliente.get("/api/usuarios", headers=admin).status_code == 200


def test_desarrollador_analiza_y_el_reporte_queda_en_bd(cliente):
    admin = _login(cliente, ADMIN_CORREO, "admin123")
    dev = _crear(cliente, admin, "dev2@test.com", "Desarrollador")

    r = _analizar(cliente, dev)
    assert r.status_code == 200, r.text
    rep = r.json()
    assert rep["proyecto"] == "AtuneraPacifico"
    assert {h["id"] for h in rep["hallazgos"]} == {"SEG-001", "SEG-002", "MEM-004", "GOV-001", "PERF-001"}
    # El reporte lleva ids, no datos personales
    yo = cliente.get("/api/auth/yo", headers=dev).json()
    assert rep["usuario_id"] == yo["id"]
    assert rep["reporte_id"]
    assert "correo" not in rep

    historial = cliente.get("/api/reportes", headers=dev).json()
    assert rep["reporte_id"] in [h["reporte_id"] for h in historial]
    assert cliente.get(f"/api/reportes/{rep['reporte_id']}", headers=dev).json()["stats"] == rep["stats"]


def test_auditor_no_analiza_pero_ve_y_evalua(cliente):
    admin = _login(cliente, ADMIN_CORREO, "admin123")
    dev = _crear(cliente, admin, "dev3@test.com", "Desarrollador")
    auditor = _crear(cliente, admin, "aud@test.com", "Auditor")

    assert _analizar(cliente, auditor).status_code == 403

    rep = _analizar(cliente, dev).json()
    assert rep["reporte_id"] in [h["reporte_id"] for h in cliente.get("/api/reportes", headers=auditor).json()]

    hallazgo_id = rep["hallazgos"][0]["hallazgo_id"]
    assert cliente.patch(f"/api/hallazgos/{hallazgo_id}", headers=dev, json={"estado": "Solucionado"}).status_code == 403
    r = cliente.patch(f"/api/hallazgos/{hallazgo_id}", headers=auditor, json={"estado": "Solucionado"})
    assert r.status_code == 200
    detalle = cliente.get(f"/api/reportes/{rep['reporte_id']}", headers=auditor).json()
    assert detalle["hallazgos"][0]["estado"] == "Solucionado"


def test_desarrollador_no_ve_reportes_ajenos(cliente):
    admin = _login(cliente, ADMIN_CORREO, "admin123")
    dev_a = _crear(cliente, admin, "dev.a@test.com", "Desarrollador")
    dev_b = _crear(cliente, admin, "dev.b@test.com", "Desarrollador")
    rep = _analizar(cliente, dev_a).json()
    assert cliente.get(f"/api/reportes/{rep['reporte_id']}", headers=dev_b).status_code == 404


def test_regla_desactivada_no_se_ejecuta(cliente):
    admin = _login(cliente, ADMIN_CORREO, "admin123")
    assert cliente.patch("/api/reglas/GOV-001", headers=admin, json={"activa": False}).status_code == 200
    try:
        rep = _analizar(cliente, admin).json()
        assert "GOV-001" not in {h["id"] for h in rep["hallazgos"]}
    finally:
        cliente.patch("/api/reglas/GOV-001", headers=admin, json={"activa": True})


def test_no_se_puede_dejar_el_sistema_sin_admin(cliente):
    admin = _login(cliente, ADMIN_CORREO, "admin123")
    yo = cliente.get("/api/auth/yo", headers=admin).json()
    r = cliente.patch(f"/api/usuarios/{yo['id']}", headers=admin, json={"rol": "Auditor"})
    assert r.status_code == 400


def test_cambiar_contrasena(cliente):
    admin = _login(cliente, ADMIN_CORREO, "admin123")
    dev = _crear(cliente, admin, "pw@test.com", "Desarrollador")
    assert cliente.post("/api/auth/yo/contrasena", headers=dev, json={"actual": "mala", "nueva": "otra-clave-1"}).status_code == 400
    assert cliente.post("/api/auth/yo/contrasena", headers=dev, json={"actual": "clave-segura", "nueva": "otra-clave-1"}).status_code == 204
    _login(cliente, "pw@test.com", "otra-clave-1")


TODAS = {"SEG-001", "SEG-002", "MEM-004", "GOV-001", "PERF-001"}


def test_por_defecto_se_aplican_todas_las_reglas(cliente):
    admin = _login(cliente, ADMIN_CORREO, "admin123")
    dev = _crear(cliente, admin, "crit1@test.com", "Desarrollador")
    rep = _analizar(cliente, dev).json()
    assert {c["codigo"] for c in rep["criterios"]} == TODAS
    assert all(c["evaluada"] for c in rep["criterios"])


def test_desarrollador_puede_quitar_reglas_antes_de_analizar(cliente):
    admin = _login(cliente, ADMIN_CORREO, "admin123")
    dev = _crear(cliente, admin, "crit2@test.com", "Desarrollador")
    rep = _analizar(cliente, dev, ["SEG-001", "SEG-002"]).json()
    assert {c["codigo"] for c in rep["criterios"]} == {"SEG-001", "SEG-002"}
    assert {h["id"] for h in rep["hallazgos"]} == {"SEG-001", "SEG-002"}
    # Solo el módulo con reglas aplicadas recibe porcentaje de cumplimiento
    assert list(rep["cumplimiento_por_modulo"]) == ["Módulo 1: Seguridad"]
    assert _analizar(cliente, dev, []).status_code == 200  # vacío = todas
    assert _analizar(cliente, dev, ["NO-EXISTE"]).status_code == 400


def test_auditor_elige_criterios_y_se_recalculan_las_metricas(cliente):
    admin = _login(cliente, ADMIN_CORREO, "admin123")
    dev = _crear(cliente, admin, "crit3@test.com", "Desarrollador")
    auditor = _crear(cliente, admin, "crit-aud@test.com", "Auditor")
    rep = _analizar(cliente, dev).json()
    url = f"/api/reportes/{rep['reporte_id']}/criterios"

    assert cliente.put(url, headers=dev, json={"evaluadas": ["SEG-001"]}).status_code == 403
    assert cliente.put(url, headers=auditor, json={"evaluadas": []}).status_code == 400

    r = cliente.put(url, headers=auditor, json={"evaluadas": ["SEG-001", "MEM-004"]})
    assert r.status_code == 200, r.text
    nuevo = r.json()
    assert {h["id"] for h in nuevo["hallazgos"]} == {"SEG-001", "MEM-004"}
    assert nuevo["stats"]["vulnerabilidades"] == 2
    assert set(nuevo["cumplimiento_por_modulo"]) == {"Módulo 1: Seguridad", "Módulo 3: Memoria"}
    assert {c["codigo"] for c in nuevo["criterios"] if c["evaluada"]} == {"SEG-001", "MEM-004"}

    # La selección queda guardada: el desarrollador también la ve
    visto = cliente.get(f"/api/reportes/{rep['reporte_id']}", headers=dev).json()
    assert visto["stats"]["vulnerabilidades"] == 2
    fila = [h for h in cliente.get("/api/reportes", headers=auditor).json() if h["reporte_id"] == rep["reporte_id"]][0]
    assert (fila["criterios_evaluados"], fila["criterios_total"]) == (2, 5)
