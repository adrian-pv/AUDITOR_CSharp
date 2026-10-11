import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.ast_bridge import load_ast_fixture, parse_project_files
from engine.orchestrator import reglas_del_catalogo, run_engine
from engine.owasp import OWASP_2021, OWASP_2025

FIXTURE = Path(__file__).parent / "fixtures" / "atunerapacifico_ast.json"
PROYECTO = Path(__file__).parent / "fixtures" / "AtuneraPacifico"


def test_cada_regla_del_catalogo_detecta_su_caso_en_el_proyecto_de_muestra():
    reporte = run_engine(load_ast_fixture(FIXTURE))
    detectadas = {h["id"] for h in reporte["hallazgos"]}
    assert detectadas == {r.codigo for r in reglas_del_catalogo()}


def test_el_codigo_seguro_no_genera_falsos_positivos():
    reporte = run_engine(load_ast_fixture(FIXTURE))
    # BuscarSeguro (ProductController.cs, líneas 17-22) usa parámetros y 'using var'
    assert not [h for h in reporte["hallazgos"] if h["archivo"] == "Controllers/ProductController.cs" and 17 <= h["linea"] <= 22]


def test_catalogo_cubre_owasp_top10_2021_y_2025():
    reglas = reglas_del_catalogo()
    assert {r.owasp_2021 for r in reglas if r.owasp_2021} == set(OWASP_2021)
    assert {r.owasp_2025 for r in reglas if r.owasp_2025} == set(OWASP_2025)


def test_stats_agregadas_son_consistentes():
    ast_files = load_ast_fixture(FIXTURE)
    reporte = run_engine(ast_files)
    assert reporte["stats"]["loc_total"] == sum(f["loc"] for f in ast_files if f.get("kind", "csharp") == "csharp")
    assert reporte["stats"]["vulnerabilidades"] == len(reporte["hallazgos"])
    assert 0 <= reporte["stats"]["score_gobierno"] <= 100


def test_lee_csproj_y_appsettings_sin_roslyn():
    archivos = {f["file"]: f for f in parse_project_files(PROYECTO)}
    paquetes = {p["name"]: p["version"] for p in archivos["AtuneraPacifico.csproj"]["packages"]}
    assert paquetes["Newtonsoft.Json"] == "12.0.3"
    ajustes = {s["key"]: s["value"] for s in archivos["appsettings.json"]["settings"]}
    assert ajustes["DetailedErrors"] == "true" and ajustes["AllowedHosts"] == "*"


def test_patron_nuevo_se_detecta_sin_cambiar_codigo():
    """Caso del ingeniero: aparece un carácter especial nuevo y el admin lo agrega a la regla."""
    ast = [{"file": "X.cs", "kind": "csharp", "loc": 3, "concatenations": [
        {"line": 2, "text": "\"ruta¬\" + x", "literal_parts": ["ruta¬"], "has_dynamic": True}]}]
    seg004 = next(r for r in reglas_del_catalogo() if r.codigo == "SEG-004")
    assert run_engine(ast, [seg004])["hallazgos"] == []
    seg004.patrones.append("¬")
    assert [h["id"] for h in run_engine(ast, [seg004])["hallazgos"]] == ["SEG-004"]
