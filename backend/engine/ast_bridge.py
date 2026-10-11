"""
Puente entre Python y la interfaz de programación Roslyn (.NET).

La detección NO se hace sobre texto plano: se hace sobre el árbol de sintaxis
abstracta (AST) que construye Roslyn. `roslyn-bridge/` es un programa de
consola en C# que recorre ese árbol y exporta, por cada archivo .cs, solo los
HECHOS que las reglas necesitan. El puente no decide qué es una
vulnerabilidad: eso lo deciden las reglas (con sus patrones editables).

Además de los .cs, este módulo lee los archivos de proyecto (.csproj) y de
configuración (appsettings*.json), que no requieren Roslyn.

Esquema del AST simplificado (una entrada por archivo):

  C# (kind = "csharp"):
  {
    "file": "Controllers/AuthController.cs", "kind": "csharp", "loc": 21,
    "declarations":   [{"kind": "property|field|variable", "name", "type", "modifiers", "line", "used"?}],
    "literals":       [{"kind": "string", "value", "line", "assigned_to"}],
    "invocations":    [{"kind": "call|new", "name", "target", "line",
                        "args": [{"text", "literal", "value", "dynamic", "concatenated", "literal_parts"}]}],
    "assignments":    [{"target", "member", "value", "line", "concatenated", "literal_parts"}],
    "concatenations": [{"line", "text", "literal_parts", "has_dynamic"}],
    "classes":        [{"name", "line", "attributes", "bases", "methods": [{"name", "line", "attributes"}]}],
    "catches":        [{"line", "type", "empty", "rethrows", "calls"}],
    "comparisons":    [{"line", "op", "left", "right"}],
    "disposables":    [{"type", "variable", "line", "wrapped_in_using", "disposed_explicitly"}]
  }

  Proyecto (kind = "csproj"):   {"file", "kind", "loc", "packages": [{"name", "version", "line"}]}
  Configuración (kind = "config"): {"file", "kind", "loc", "settings": [{"key": "A:B:C", "value", "line"}]}
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROSLYN_BRIDGE_DIR = Path(__file__).resolve().parents[2] / "roslyn-bridge"
ROSLYN_BRIDGE_DLL = ROSLYN_BRIDGE_DIR / "bin" / "Release" / "net10.0" / "RoslynBridge.dll"

CARPETAS_IGNORADAS = {"bin", "obj", "node_modules", ".git", ".vs"}


class RoslynBridgeNotBuilt(RuntimeError):
    """El proyecto roslyn-bridge todavía no fue compilado con `dotnet build`."""


def es_archivo_de_proyecto(nombre: str) -> bool:
    n = nombre.lower().rsplit("/", 1)[-1]
    return n.endswith(".csproj") or (n.startswith("appsettings") and n.endswith(".json"))


def parse_solution(source_dir: Path) -> list[dict]:
    """AST de todos los .cs (vía RoslynBridge) más los .csproj y appsettings*.json."""
    source_dir = Path(source_dir)
    resultado: list[dict] = []

    if any(_archivos(source_dir, "*.cs")):
        if not ROSLYN_BRIDGE_DLL.exists():
            raise RoslynBridgeNotBuilt(
                "No se encontró RoslynBridge.dll. Compile el puente primero:\n"
                "  cd roslyn-bridge && dotnet build -c Release"
            )
        proc = subprocess.run(
            ["dotnet", str(ROSLYN_BRIDGE_DLL), str(source_dir)],
            capture_output=True, text=True, encoding="utf-8", check=True,
        )
        resultado.extend(json.loads(proc.stdout))

    resultado.extend(parse_project_files(source_dir))
    return resultado


def _archivos(raiz: Path, patron: str):
    for ruta in sorted(raiz.rglob(patron)):
        if not CARPETAS_IGNORADAS & set(ruta.relative_to(raiz).parts):
            yield ruta


def parse_project_files(raiz: Path) -> list[dict]:
    """Lee .csproj (paquetes NuGet) y appsettings*.json (ajustes) sin necesidad de Roslyn."""
    raiz = Path(raiz)
    salida = []
    for ruta in _archivos(raiz, "*"):
        if not ruta.is_file() or not es_archivo_de_proyecto(ruta.name):
            continue
        texto = ruta.read_text(encoding="utf-8-sig", errors="replace")
        relativo = ruta.relative_to(raiz).as_posix()
        if ruta.suffix.lower() == ".csproj":
            salida.append({"file": relativo, "kind": "csproj", "loc": texto.count("\n") + 1, "packages": _paquetes(texto)})
        else:
            salida.append({"file": relativo, "kind": "config", "loc": texto.count("\n") + 1, "settings": _ajustes(texto)})
    return salida


def _paquetes(texto: str) -> list[dict]:
    paquetes = []
    for m in re.finditer(r"<PackageReference\b([^>]*?)(/?>)", texto, re.IGNORECASE | re.DOTALL):
        attrs = dict((k.lower(), v) for k, v in re.findall(r'(\w+)\s*=\s*"([^"]*)"', m.group(1)))
        nombre = attrs.get("include") or attrs.get("update")
        if not nombre:
            continue
        version = attrs.get("version")
        if version is None and m.group(2) == ">":  # <Version>x</Version> como elemento hijo
            fin = texto.find("</PackageReference>", m.end())
            hijo = re.search(r"<Version>\s*([^<]+?)\s*</Version>", texto[m.end():fin], re.IGNORECASE)
            version = hijo.group(1) if hijo else None
        paquetes.append({"name": nombre, "version": version, "line": texto.count("\n", 0, m.start()) + 1})
    return paquetes


def _ajustes(texto: str) -> list[dict]:
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError:
        return []
    lineas = texto.splitlines()
    salida: list[dict] = []

    def linea_de(clave: str, desde: int) -> int:
        for i in range(desde, len(lineas)):
            if f'"{clave}"' in lineas[i]:
                return i + 1
        return desde + 1

    def recorrer(nodo, prefijo: list[str], desde: int) -> int:
        if isinstance(nodo, dict):
            for k, v in nodo.items():
                ln = linea_de(k, desde)
                if isinstance(v, (dict, list)):
                    desde = recorrer(v, prefijo + [k], ln - 1)
                else:
                    salida.append({"key": ":".join(prefijo + [k]), "value": json.dumps(v) if isinstance(v, bool) else v, "line": ln})
                    desde = ln
        elif isinstance(nodo, list):
            for i, v in enumerate(nodo):
                desde = recorrer(v, prefijo + [str(i)], desde)
        return desde

    recorrer(datos, [], 0)
    for s in salida:  # true/false/null como texto, igual que en .NET
        if s["value"] is None:
            s["value"] = ""
        s["value"] = str(s["value"]).strip('"') if not isinstance(s["value"], str) else s["value"]
    return salida


def load_ast_fixture(fixture_path: Path) -> list[dict]:
    """AST ya serializado en disco (pruebas unitarias, sin necesidad del SDK de .NET)."""
    with open(fixture_path, encoding="utf-8") as fh:
        return json.load(fh)
