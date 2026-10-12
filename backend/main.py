"""
Punto de entrada de línea de comandos del motor de gobierno y auditoría.

Uso:
    python main.py <ruta-a-la-solucion-csharp> [--out reporte.json]

Flujo (ver Capítulo II, Metodología):
    1. RoslynBridge parsea cada archivo .cs de la solución y produce el AST
       simplificado (ast_bridge.parse_solution).
    2. El orquestador corre las reglas de los cuatro módulos contra ese AST.
    3. El reporte agregado se escribe a disco como JSON, listo para que el
       frontend lo consuma (ver frontend/sample-data/report.sample.json
       para el formato exacto sin necesidad de correr el motor).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine.ast_bridge import RoslynBridgeNotBuilt, parse_solution
from engine.orchestrator import run_engine
from engine.report import write_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Motor de gobierno y auditoría de código C#")
    parser.add_argument("solution_path", type=Path, help="Carpeta raíz de la solución .NET a auditar")
    parser.add_argument("--out", type=Path, default=Path("reporte.json"), help="Ruta de salida del reporte")
    args = parser.parse_args()

    try:
        ast_files = parse_solution(args.solution_path)
    except RoslynBridgeNotBuilt as exc:
        print(f"[!] {exc}", file=sys.stderr)
        sys.exit(1)

    reporte = run_engine(ast_files)
    destino = write_report(reporte, args.out)
    print(f"Reporte generado en {destino}")
    v = reporte["veredicto"]
    textos = {
        "APROBADO": "APROBADO: sin hallazgos.",
        "APROBADO_CON_ADVERTENCIAS": f"APROBADO CON ADVERTENCIAS: {v['advertencias']} advertencia(s), {v['bajos']} de severidad baja.",
        "NO_APROBADO": f"NO APROBADO: {v['criticos']} hallazgo(s) crítico(s) en {', '.join(v['reglas_criticas'])}.",
    }
    print(textos[v["estado"]])


if __name__ == "__main__":
    main()
