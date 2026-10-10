"""
Puente entre Python y la interfaz de programación Roslyn (.NET).

La detección heurística NO se hace analizando texto plano: se hace sobre un
árbol de sintaxis abstracta (AST) que expone Roslyn. Como Roslyn corre sobre
.NET y el motor de reglas corre en Python, `roslyn-bridge/` es un pequeño
proyecto de consola en C# que:

  1. Recibe la ruta de un archivo .cs (o de una carpeta/solución) como
     argumento.
  2. Construye el árbol de sintaxis con `CSharpSyntaxTree.ParseText`.
  3. Recorre el árbol y serializa a JSON únicamente los nodos que interesan
     a las reglas del motor (declaraciones, literales, invocaciones), según
     el esquema descrito abajo.
  4. Imprime el JSON resultante a stdout.

Este módulo invoca ese binario como subproceso y valida/normaliza el JSON
antes de entregárselo al orquestador.

Esquema del AST simplificado (una entrada por archivo):
{
  "file": "Controllers/AuthController.cs",
  "loc": 21,
  "declarations": [
    {"kind": "field|property|variable", "name": "AdminPassword",
     "type": "string", "modifiers": ["private", "const"], "line": 10}
  ],
  "literals": [
    {"kind": "string", "value": "pruebas21_SecretPassword_2026",
     "line": 10, "assigned_to": "AdminPassword"}
  ],
  "invocations": [
    {"method": "SqlCommand.ctor", "line": 14, "arguments_are_concatenated": true}
  ],
  "disposables": [
    {"type": "SqlConnection", "variable": "connection", "line": 9,
     "wrapped_in_using": false, "disposed_explicitly": false}
  ]
}
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROSLYN_BRIDGE_DIR = Path(__file__).resolve().parents[2] / "roslyn-bridge"
ROSLYN_BRIDGE_DLL = ROSLYN_BRIDGE_DIR / "bin" / "Release" / "net10.0" / "RoslynBridge.dll"


class RoslynBridgeNotBuilt(RuntimeError):
    """El proyecto roslyn-bridge todavía no fue compilado con `dotnet build`."""


def parse_solution(source_dir: Path) -> list[dict]:
    """
    Ejecuta RoslynBridge sobre todos los .cs bajo `source_dir` y retorna
    la lista de ASTs simplificados (uno por archivo), según el esquema
    descrito en el docstring del módulo.
    """
    if not ROSLYN_BRIDGE_DLL.exists():
        raise RoslynBridgeNotBuilt(
            "No se encontró RoslynBridge.dll. Compile el puente primero:\n"
            "  cd roslyn-bridge && dotnet build -c Release"
        )

    proc = subprocess.run(
        ["dotnet", str(ROSLYN_BRIDGE_DLL), str(source_dir)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def load_ast_fixture(fixture_path: Path) -> list[dict]:
    """
    Carga un AST simplificado ya serializado en disco (usado por las
    pruebas unitarias y por la demo, para no requerir el SDK de .NET
    instalado en cada entorno de desarrollo).
    """
    with open(fixture_path, encoding="utf-8") as fh:
        return json.load(fh)
