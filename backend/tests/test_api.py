"""Pruebas de la API: inicio de sesión, roles, análisis guardado en BD e historial."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.reportes
import server
from engine.ast_bridge import load_ast_fixture
from modules import CATALOGO_INICIAL
from persistencia.inicializacion import ADMIN_CORREO

FIXTURE = Path(__file__).parent / "fixtures" / "atunerapacifico_ast.json"
TODAS = {r["codigo"] for r in CATALOGO_INICIAL}


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
    assert {h["id"] for h in rep["hallazgos"]} == TODAS
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
    assert all(h["owasp_2021"] and h["owasp_2025"] for h in rep["hallazgos"])
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
    esperado = sum(1 for h in rep["hallazgos"] if h["id"] in ("SEG-001", "MEM-004"))
    assert nuevo["stats"]["vulnerabilidades"] == esperado
    assert set(nuevo["cumplimiento_por_modulo"]) == {"Módulo 1: Seguridad", "Módulo 3: Memoria"}
    assert {c["codigo"] for c in nuevo["criterios"] if c["evaluada"]} == {"SEG-001", "MEM-004"}

    # La selección queda guardada: el desarrollador también la ve
    visto = cliente.get(f"/api/reportes/{rep['reporte_id']}", headers=dev).json()
    assert visto["stats"]["vulnerabilidades"] == esperado
    fila = [h for h in cliente.get("/api/reportes", headers=auditor).json() if h["reporte_id"] == rep["reporte_id"]][0]
    assert (fila["criterios_evaluados"], fila["criterios_total"]) == (2, len(TODAS))


# ----------------------------------------------------------------------------- reglas configurables


def _regla_base(**cambios):
    datos = {
        "nombre": "Uso de Thread.Abort", "modulo": "Módulo 2: Rendimiento", "categoria": "Rendimiento (.NET)",
        "severidad": "ADVERTENCIA", "tipo_deteccion": "llamada_a_metodo", "patrones": ["Thread.Abort"],
        "mensaje": "{detalle} Interrumpe hilos de forma insegura.", "recomendacion": "Usar CancellationToken.",
    }
    datos.update(cambios)
    return datos


def test_plantillas_y_owasp_disponibles(cliente):
    admin = _login(cliente, ADMIN_CORREO, "admin123")
    p = cliente.get("/api/reglas/plantillas", headers=admin).json()
    assert "concatenacion_con_patron" in {d["tipo"] for d in p["detectores"]}
    assert len(p["owasp_2021"]) == len(p["owasp_2025"]) == 10


def test_admin_crea_regla_nueva_con_codigo_automatico(cliente):
    admin = _login(cliente, ADMIN_CORREO, "admin123")
    dev = _crear(cliente, admin, "regla-dev@test.com", "Desarrollador")
    assert cliente.post("/api/reglas", headers=dev, json=_regla_base()).status_code == 403
    r = cliente.post("/api/reglas", headers=admin, json=_regla_base())
    assert r.status_code == 201, r.text
    assert r.json()["codigo"] == "PERF-002" and r.json()["predefinida"] is False


def test_admin_agrega_caracter_especial_y_el_analisis_lo_detecta(cliente, monkeypatch):
    admin = _login(cliente, ADMIN_CORREO, "admin123")
    ast = [{"file": "X/Rutas.cs", "kind": "csharp", "loc": 5, "concatenations": [
        {"line": 3, "text": "\"/datos¬\" + nombre", "literal_parts": ["/datos¬"], "has_dynamic": True}]}]
    monkeypatch.setattr(api.reportes, "parse_solution", lambda _r: ast)

    antes = _analizar(cliente, admin, ["SEG-004"]).json()
    assert antes["hallazgos"] == []

    regla = next(x for x in cliente.get("/api/reglas", headers=admin).json() if x["codigo"] == "SEG-004")
    regla["patrones"].append("¬")
    r = cliente.put("/api/reglas/SEG-004", headers=admin, json=regla)
    assert r.status_code == 200, r.text
    try:
        despues = _analizar(cliente, admin, ["SEG-004"]).json()
        assert [h["id"] for h in despues["hallazgos"]] == ["SEG-004"]
        assert "«¬»" in despues["hallazgos"][0]["descripcion"]
    finally:
        regla["patrones"].remove("¬")
        cliente.put("/api/reglas/SEG-004", headers=admin, json=regla)


def test_validaciones_de_regla(cliente):
    admin = _login(cliente, ADMIN_CORREO, "admin123")
    assert cliente.post("/api/reglas", headers=admin, json=_regla_base(patrones=[])).status_code == 422
    assert cliente.post("/api/reglas", headers=admin, json=_regla_base(tipo_deteccion="inventado")).status_code == 422
    assert cliente.post("/api/reglas", headers=admin, json=_regla_base(owasp_2021="A11:2021")).status_code == 422
    assert cliente.post("/api/reglas", headers=admin, json=_regla_base(
        tipo_deteccion="nomenclatura", patrones=["[A-Z"])).status_code == 422
    seg001 = next(x for x in cliente.get("/api/reglas", headers=admin).json() if x["codigo"] == "SEG-001")
    seg001["tipo_deteccion"] = "llamada_a_metodo"
    assert cliente.put("/api/reglas/SEG-001", headers=admin, json=seg001).status_code == 422


# ----------------------------------------------------------------------------- reporte como archivo .json


def test_exportar_y_cargar_reporte_json_sin_guardar(cliente):
    admin = _login(cliente, ADMIN_CORREO, "admin123")
    dev = _crear(cliente, admin, "json-dev@test.com", "Desarrollador")
    auditor = _crear(cliente, admin, "json-aud@test.com", "Auditor")
    rep = _analizar(cliente, dev).json()
    cliente.put(f"/api/reportes/{rep['reporte_id']}/criterios", headers=auditor, json={"evaluadas": ["SEG-001", "MEM-004"]})

    r = cliente.get(f"/api/reportes/{rep['reporte_id']}/exportar", headers=dev)
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"] and ".json" in r.headers["content-disposition"]
    doc = r.json()
    assert doc["formato"] == "AUDITOR_CSharp/reporte" and doc["version"] == 1
    # El archivo trae TODOS los hallazgos, no solo los de los criterios evaluados
    assert len(doc["hallazgos"]) == len(rep["hallazgos"])
    assert "hallazgo_id" not in doc["hallazgos"][0]

    historial_antes = len(cliente.get("/api/reportes", headers=admin).json())
    # Un auditor carga el archivo: se ve igual que el reporte guardado
    vista = cliente.post("/api/reportes/vista", headers=auditor, json=doc).json()
    assert vista["importado"] is True
    guardado = cliente.get(f"/api/reportes/{rep['reporte_id']}", headers=auditor).json()
    assert vista["stats"] == guardado["stats"]
    assert vista["cumplimiento_por_modulo"] == guardado["cumplimiento_por_modulo"]
    # ... y no se guardó nada nuevo
    assert len(cliente.get("/api/reportes", headers=admin).json()) == historial_antes


def test_reporte_cargado_recalcula_metricas_y_no_confia_en_el_archivo(cliente):
    admin = _login(cliente, ADMIN_CORREO, "admin123")
    doc = cliente.get(f"/api/reportes/{_analizar(cliente, admin).json()['reporte_id']}/exportar", headers=admin).json()

    doc["stats"] = {"loc_total": doc["loc_total"], "vulnerabilidades": 0, "score_gobierno": 100}  # manipulado
    vista = cliente.post("/api/reportes/vista", headers=admin, json=doc).json()
    assert vista["stats"]["vulnerabilidades"] == len(doc["hallazgos"])

    for c in doc["criterios"]:
        c["evaluada"] = c["codigo"] == "SEG-001"
    vista = cliente.post("/api/reportes/vista", headers=admin, json=doc).json()
    assert {h["id"] for h in vista["hallazgos"]} == {"SEG-001"}
    assert list(vista["cumplimiento_por_modulo"]) == ["Módulo 1: Seguridad"]


def test_archivo_json_invalido_se_rechaza(cliente):
    admin = _login(cliente, ADMIN_CORREO, "admin123")
    base = {"proyecto": "X", "loc_total": 10, "criterios": [], "hallazgos": []}
    h = {"id": "SEG-001", "modulo": "Módulo 1: Seguridad", "severidad": "CRÍTICO", "archivo": "a.cs", "linea": 1}

    assert cliente.post("/api/reportes/vista", json=base).status_code == 401
    assert cliente.post("/api/reportes/vista", headers=admin, json={**base, "formato": "otro"}).status_code == 422
    assert cliente.post("/api/reportes/vista", headers=admin, json={**base, "version": 99}).status_code == 422
    malos = [{**h, "severidad": "GRAVE"}, {**h, "estado": "Hackeado"}, {**h, "linea": -1}]
    for malo in malos:
        assert cliente.post("/api/reportes/vista", headers=admin, json={**base, "hallazgos": [malo]}).status_code == 422
    huerfano = {**base, "criterios": [{"codigo": "MEM-004", "modulo": "Módulo 3: Memoria", "severidad": "BAJO"}], "hallazgos": [h]}
    assert cliente.post("/api/reportes/vista", headers=admin, json=huerfano).status_code == 422

    # Archivos antiguos de la carpeta reports/ (sin formato ni criterios) siguen funcionando
    antiguo = {"proyecto": "X", "stats": {"loc_total": 50}, "hallazgos": [h]}
    vista = cliente.post("/api/reportes/vista", headers=admin, json=antiguo).json()
    assert vista["stats"]["vulnerabilidades"] == 1 and vista["criterios"][0]["codigo"] == "SEG-001"
