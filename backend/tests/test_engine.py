import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.ast_bridge import load_ast_fixture
from engine.orchestrator import run_engine

FIXTURE = Path(__file__).parent / "fixtures" / "atunerapacifico_ast.json"


def test_detecta_los_cinco_hallazgos_esperados():
    ast_files = load_ast_fixture(FIXTURE)
    reporte = run_engine(ast_files)

    ids_detectados = {h["id"] for h in reporte["hallazgos"]}
    assert ids_detectados == {"SEG-001", "SEG-002", "MEM-004", "GOV-001", "PERF-001"}


def test_stats_agregadas_son_consistentes():
    ast_files = load_ast_fixture(FIXTURE)
    reporte = run_engine(ast_files)

    assert reporte["stats"]["loc_total"] == sum(f["loc"] for f in ast_files)
    assert reporte["stats"]["vulnerabilidades"] == len(reporte["hallazgos"])
    assert 0 <= reporte["stats"]["score_gobierno"] <= 100


def test_appsettings_sin_hallazgos_no_rompe_el_motor():
    ast_files = load_ast_fixture(FIXTURE) + [
        {"file": "appsettings.json", "loc": 9, "declarations": [], "literals": [], "invocations": [], "disposables": []}
    ]
    reporte = run_engine(ast_files)
    assert reporte["stats"]["loc_total"] == sum(f["loc"] for f in ast_files)
