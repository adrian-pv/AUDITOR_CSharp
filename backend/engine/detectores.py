"""
Detectores genéricos del motor de reglas.

Cada regla de la base de datos indica un `tipo_deteccion` (uno de los
detectores de este módulo) y una lista de `patrones` que el Administrador
puede editar sin tocar código: palabras clave, nombres de métodos o tipos,
caracteres especiales, pares "Miembro=valor", paquetes NuGet, etc.

Un detector recibe la regla y el AST simplificado de UN archivo (ver
engine/ast_bridge.py) y devuelve una lista de (línea, detalle). El motor
convierte cada resultado en un hallazgo usando el mensaje de la regla.

Todas las comparaciones son sin distinguir mayúsculas de minúsculas.
"""

from __future__ import annotations

import fnmatch
import re
from typing import Callable

from engine.regla_def import ReglaDef

Resultado = list[tuple[int, str]]


# ============================================================================ utilidades


def _norm(s: str | None) -> str:
    return (s or "").lower()


def _sin_separadores(s: str | None) -> str:
    return re.sub(r"[_\-\s.]", "", _norm(s))


def _coincide_llamada(patron: str, inv: dict) -> bool:
    """'Process.Start' coincide con System.Diagnostics.Process.Start; 'SqlCommand' con new SqlCommand(...)."""
    p = _norm(patron).strip()
    nombre, objetivo = _norm(inv.get("name")), _norm(inv.get("target"))
    return bool(p) and (nombre == p or objetivo == p or objetivo.endswith("." + p))


def _patrones(regla: ReglaDef) -> list[str]:
    return [p for p in (regla.patrones or []) if str(p).strip()]


def _param(regla: ReglaDef, nombre: str, defecto):
    return (regla.parametros or {}).get(nombre, defecto)


def _es_csharp(ast: dict) -> bool:
    return ast.get("kind", "csharp") == "csharp"


# ============================================================================ detectores


def literal_asignado(regla: ReglaDef, ast: dict) -> Resultado:
    """Texto fijo asignado a una variable/propiedad cuyo nombre contiene un patrón (p. ej. 'password')."""
    claves = [_sin_separadores(p) for p in _patrones(regla)]
    res = []
    for lit in ast.get("literals", []):
        destino = lit.get("assigned_to")
        if not destino or not (lit.get("value") or "").strip():
            continue
        if any(c and c in _sin_separadores(destino) for c in claves):
            res.append((lit["line"], f"Se asigna un valor fijo a '{destino}'."))
    return res


def concatenacion_con_patron(regla: ReglaDef, ast: dict) -> Resultado:
    """Cadena armada con datos dinámicos cuyo texto fijo contiene caracteres/fragmentos peligrosos."""
    patrones = _patrones(regla)
    res = []
    for c in ast.get("concatenations", []):
        if not c.get("has_dynamic"):
            continue
        texto = " ".join(c.get("literal_parts", []))
        hallados = [p for p in patrones if p.lower() in texto.lower()]
        if hallados:
            lista = ", ".join(f"«{h}»" for h in hallados)
            res.append((c["line"], f"La cadena mezcla datos externos con {lista}: {c.get('text', '')[:120]}"))
    return res


def llamada_con_argumento_dinamico(regla: ReglaDef, ast: dict) -> Resultado:
    """Llamada a un método/constructor sensible (patrones) con argumentos armados dinámicamente."""
    modo = _param(regla, "modo", "concatenado")  # "concatenado" | "dinamico"
    solo_primero = bool(_param(regla, "solo_primer_argumento", False))
    patrones = _patrones(regla)
    res = []
    for inv in ast.get("invocations", []):
        if not any(_coincide_llamada(p, inv) for p in patrones):
            continue
        argumentos = inv.get("args", [])[:1] if solo_primero else inv.get("args", [])
        clave = "concatenated" if modo == "concatenado" else "dynamic"
        riesgosos = [a for a in argumentos if a.get(clave)]
        if riesgosos:
            res.append((inv["line"], f"'{inv.get('target')}' recibe un valor construido dinámicamente: {riesgosos[0].get('text', '')[:120]}"))
    for asig in ast.get("assignments", []):
        if any(_norm(asig.get("member")) == _norm(p) for p in patrones) and asig.get("concatenated"):
            res.append((asig["line"], f"'{asig.get('target')}' se arma por concatenación: {asig.get('value', '')[:120]}"))
    return res


def llamada_a_metodo(regla: ReglaDef, ast: dict) -> Resultado:
    """Uso de un método, clase o API considerada insegura (patrones)."""
    patrones = _patrones(regla)
    res = []
    for inv in ast.get("invocations", []):
        if any(_coincide_llamada(p, inv) for p in patrones):
            verbo = "Se instancia" if inv.get("kind") == "new" else "Se invoca"
            res.append((inv["line"], f"{verbo} '{inv.get('target')}'."))
    return res


def _coincide_valor(esperado: str, valor: str) -> bool:
    v = _norm(valor).replace(" ", "")
    e = _norm(esperado).replace(" ", "")
    return v == e or v.endswith("." + e) or v.endswith("=>" + e)


def asignacion_insegura(regla: ReglaDef, ast: dict) -> Resultado:
    """Asignación 'Miembro = valor' peligrosa. Patrón: 'Miembro=valor' (o solo 'Miembro')."""
    res = []
    for patron in _patrones(regla):
        miembro, _, valor = patron.partition("=")
        for asig in ast.get("assignments", []):
            if _norm(asig.get("member")) != _norm(miembro).strip():
                continue
            if valor and not _coincide_valor(valor, asig.get("value", "")):
                continue
            res.append((asig["line"], f"'{asig.get('target')} = {asig.get('value', '')[:80]}'."))
    return res


def llamada_con_dato_sensible(regla: ReglaDef, ast: dict) -> Resultado:
    """Llamada (p. ej. a un logger) cuyos argumentos incluyen datos sensibles (parámetro 'palabras')."""
    palabras = [_norm(p) for p in _param(regla, "palabras", ["password", "contrasena", "token", "secret"])]
    res = []
    for inv in ast.get("invocations", []):
        if not any(_coincide_llamada(p, inv) for p in _patrones(regla)):
            continue
        texto = " ".join(_norm(a.get("text")) for a in inv.get("args", []))
        hallada = next((w for w in palabras if w and w in texto), None)
        if hallada:
            res.append((inv["line"], f"'{inv.get('target')}' registra un valor relacionado con «{hallada}»."))
    return res


VERBOS_HTTP = ["HttpPost", "HttpPut", "HttpDelete", "HttpPatch"]


def controlador_sin_atributo(regla: ReglaDef, ast: dict) -> Resultado:
    """
    Controladores de ASP.NET sin un atributo requerido (patrones).
    Parámetro 'alcance': "clase" (p. ej. falta [Authorize]) o "accion" (acciones
    con verbos HTTP que modifican datos sin, p. ej., [ValidateAntiForgeryToken]).
    """
    requeridos = {_norm(p) for p in _patrones(regla)}
    alcance = _param(regla, "alcance", "clase")
    excluir = {_norm(x) for x in _param(regla, "excluir_si", [])}
    verbos = {_norm(v) for v in _param(regla, "verbos", VERBOS_HTTP)}
    res = []
    for clase in ast.get("classes", []):
        es_controlador = clase["name"].endswith("Controller") or any(
            b.split("<")[0] in ("Controller", "ControllerBase") for b in clase.get("bases", [])
        )
        if not es_controlador:
            continue
        attrs_clase = {_norm(a) for a in clase.get("attributes", [])}
        if attrs_clase & excluir:
            continue
        if alcance == "clase":
            en_metodos = any({_norm(a) for a in m.get("attributes", [])} & requeridos for m in clase.get("methods", []))
            if not (attrs_clase & requeridos) and not en_metodos:
                res.append((clase["line"], f"El controlador '{clase['name']}' no declara ninguno de: {', '.join(_patrones(regla))}."))
        else:
            for m in clase.get("methods", []):
                attrs = {_norm(a) for a in m.get("attributes", [])}
                if attrs & verbos and not ((attrs | attrs_clase) & requeridos):
                    res.append((m["line"], f"La acción '{clase['name']}.{m['name']}' modifica datos sin {', '.join(_patrones(regla))}."))
    return res


def excepcion_mal_manejada(regla: ReglaDef, ast: dict) -> Resultado:
    """Bloques catch vacíos, o que capturan excepciones genéricas (patrones) sin registrar ni relanzar."""
    genericas = {_norm(p) for p in _patrones(regla)}
    registro = [_norm(x) for x in _param(regla, "llamadas_de_registro", ["log", "logger", "trace"])]
    res = []
    for c in ast.get("catches", []):
        tipo = c.get("type") or "(cualquier excepción)"
        if c.get("empty"):
            res.append((c["line"], f"El bloque catch de '{tipo}' está vacío: el error se ignora en silencio."))
            continue
        generica = not c.get("type") or _norm(c.get("type").split(".")[-1]) in genericas
        registra = any(any(r in _norm(llamada) for r in registro) for llamada in c.get("calls", []))
        if generica and not c.get("rethrows") and not registra:
            res.append((c["line"], f"Se captura '{tipo}' sin registrarla ni relanzarla."))
    return res


def comparacion_texto_plano(regla: ReglaDef, ast: dict) -> Resultado:
    """Comparación directa (==, Equals) de valores cuyo nombre contiene un patrón (p. ej. contraseñas)."""
    claves = [_sin_separadores(p) for p in _patrones(regla)]
    excepciones = [_norm(x) for x in _param(regla, "excepto_si_contiene", ["hash", "verify", "null"])]
    res = []
    for c in ast.get("comparisons", []):
        lados = _sin_separadores(c.get("left")) + " " + _sin_separadores(c.get("right"))
        if any(k and k in lados for k in claves) and not any(e and e in lados for e in excepciones):
            res.append((c["line"], f"Se compara directamente '{c.get('left')}' {c.get('op')} '{c.get('right')}'."))
    return res


def recurso_sin_liberar(regla: ReglaDef, ast: dict) -> Resultado:
    """Objetos de tipos IDisposable (patrones) creados sin 'using' ni Dispose()/Close()."""
    tipos = {_norm(p) for p in _patrones(regla)}
    res = []
    for d in ast.get("disposables", []):
        tipo = _norm((d.get("type") or "").split(".")[-1])
        if tipo in tipos and not d.get("wrapped_in_using") and not d.get("disposed_explicitly"):
            res.append((d["line"], f"'{d['variable']}' de tipo {d['type']} no se libera con 'using' ni Dispose()."))
    return res


def variable_no_usada(regla: ReglaDef, ast: dict) -> Resultado:
    """Variables locales declaradas que no vuelven a usarse (patrones = nombres a ignorar)."""
    ignorar = {_norm(p) for p in _patrones(regla)}
    return [
        (d["line"], f"La variable local '{d['name']}' se declara pero no se vuelve a usar.")
        for d in ast.get("declarations", [])
        if d.get("kind") == "variable" and d.get("used") is False and _norm(d["name"]) not in ignorar
    ]


def nomenclatura(regla: ReglaDef, ast: dict) -> Resultado:
    """Nombres que no cumplen la expresión regular de la regla (patrón 1) para los tipos indicados."""
    patrones = _patrones(regla)
    if not patrones:
        return []
    regex = re.compile(patrones[0])
    tipos = set(_param(regla, "tipos", ["property"]))
    modificador = _param(regla, "modificador", "public")
    res = []
    for d in ast.get("declarations", []):
        if d.get("kind") in tipos and (not modificador or modificador in d.get("modifiers", [])):
            if not regex.fullmatch(d["name"]):
                res.append((d["line"], f"'{d['name']}' no sigue la convención de nombres esperada."))
    return res


def _version(texto: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", texto or "")[:4]) or (0,)


def paquete_vulnerable(regla: ReglaDef, ast: dict) -> Resultado:
    """
    Dependencias NuGet del .csproj. Patrón 'Paquete' (cualquier versión) o
    'Paquete<versión' (versiones anteriores a la indicada). Con el parámetro
    'version_flotante' también se marcan versiones con '*' o sin versión.
    """
    res = []
    for pkg in ast.get("packages", []):
        nombre, version = pkg.get("name", ""), pkg.get("version") or ""
        for patron in _patrones(regla):
            p_nombre, sep, p_version = patron.partition("<")
            if _norm(p_nombre).strip() != _norm(nombre):
                continue
            if not sep or (version and "*" not in version and _version(version) < _version(p_version)):
                motivo = f"anterior a {p_version.strip()}" if sep else "marcada como insegura u obsoleta"
                res.append((pkg["line"], f"'{nombre}' {version or '(sin versión)'}: versión {motivo}."))
        if _param(regla, "version_flotante", True) and (not version or "*" in version):
            res.append((pkg["line"], f"'{nombre}' usa una versión flotante o sin fijar ({version or 'sin versión'})."))
    return res


def configuracion_insegura(regla: ReglaDef, ast: dict) -> Resultado:
    """Ajustes de appsettings.json. Patrón 'Clave=valor'; la clave admite '*' (p. ej. '*:RequireHttpsMetadata=false')."""
    res = []
    for patron in _patrones(regla):
        clave, _, valor = patron.partition("=")
        for s in ast.get("settings", []):
            if fnmatch.fnmatch(_norm(s["key"]), _norm(clave).strip()) and _norm(str(s["value"])) == _norm(valor).strip():
                res.append((s["line"], f"'{s['key']}' = '{s['value']}'."))
    return res


def secreto_en_configuracion(regla: ReglaDef, ast: dict) -> Resultado:
    """Secretos escritos en archivos de configuración: claves con palabras sensibles o cadenas con 'Password='."""
    claves = [_sin_separadores(p) for p in _patrones(regla)]
    marcadores = [_norm(m) for m in _param(regla, "marcadores_en_valor", ["password=", "pwd="])]
    res = []
    for s in ast.get("settings", []):
        valor = str(s.get("value") or "")
        if not valor.strip():
            continue
        ultima = _sin_separadores(s["key"].split(":")[-1])
        if any(c and c in ultima for c in claves) or any(m and m in _norm(valor) for m in marcadores):
            res.append((s["line"], f"'{s['key']}' contiene un secreto en texto plano."))
    return res


# ============================================================================ registro

PLANTILLAS: dict[str, dict] = {
    "literal_asignado": {
        "funcion": literal_asignado, "archivos": "csharp",
        "nombre": "Valor fijo asignado a un nombre sensible",
        "descripcion": "Marca textos escritos en el código que se asignan a variables, campos o propiedades cuyo nombre contiene alguno de los patrones.",
        "ayuda_patrones": "Palabras clave del nombre (p. ej. password, apikey, token).",
        "parametros": {},
    },
    "concatenacion_con_patron": {
        "funcion": concatenacion_con_patron, "archivos": "csharp",
        "nombre": "Concatenación con caracteres peligrosos",
        "descripcion": "Marca cadenas que mezclan datos externos (variables) con texto fijo que contiene alguno de los caracteres o fragmentos de la lista.",
        "ayuda_patrones": "Caracteres o fragmentos peligrosos (p. ej. ', --, ;, ../, <script). Agregue aquí cualquier carácter nuevo.",
        "parametros": {},
    },
    "llamada_con_argumento_dinamico": {
        "funcion": llamada_con_argumento_dinamico, "archivos": "csharp",
        "nombre": "Llamada sensible con datos dinámicos",
        "descripcion": "Marca llamadas a métodos o constructores sensibles cuando sus argumentos se arman con datos externos.",
        "ayuda_patrones": "Métodos, constructores o propiedades (p. ej. SqlCommand, ExecuteSqlRaw, Process.Start, CommandText).",
        "parametros": {
            "modo": {"tipo": "opcion", "opciones": ["concatenado", "dinamico"], "defecto": "concatenado",
                     "descripcion": "concatenado: solo si el argumento se arma con + o interpolación; dinamico: cualquier valor que no sea un texto fijo."},
            "solo_primer_argumento": {"tipo": "booleano", "defecto": False, "descripcion": "Revisar solo el primer argumento (p. ej. la URL)."},
        },
    },
    "llamada_a_metodo": {
        "funcion": llamada_a_metodo, "archivos": "csharp",
        "nombre": "Uso de API insegura",
        "descripcion": "Marca cualquier llamada o instanciación de las clases o métodos de la lista.",
        "ayuda_patrones": "Clases o métodos (p. ej. MD5.Create, BinaryFormatter, Random).",
        "parametros": {},
    },
    "asignacion_insegura": {
        "funcion": asignacion_insegura, "archivos": "csharp",
        "nombre": "Asignación de configuración insegura",
        "descripcion": "Marca asignaciones 'Miembro = valor' peligrosas en el código.",
        "ayuda_patrones": "Formato Miembro=valor (p. ej. ValidateLifetime=false, TypeNameHandling=All). Solo 'Miembro' marca cualquier valor.",
        "parametros": {},
    },
    "llamada_con_dato_sensible": {
        "funcion": llamada_con_dato_sensible, "archivos": "csharp",
        "nombre": "Datos sensibles enviados a un método",
        "descripcion": "Marca llamadas (p. ej. de registro/log) cuyos argumentos mencionan datos sensibles.",
        "ayuda_patrones": "Métodos a vigilar (p. ej. LogInformation, Console.WriteLine).",
        "parametros": {
            "palabras": {"tipo": "lista", "defecto": ["password", "contrasena", "token", "secret"], "descripcion": "Palabras que indican un dato sensible."},
        },
    },
    "controlador_sin_atributo": {
        "funcion": controlador_sin_atributo, "archivos": "csharp",
        "nombre": "Controlador sin atributo de seguridad",
        "descripcion": "Marca controladores de ASP.NET (o sus acciones POST/PUT/DELETE) que no declaran ninguno de los atributos de la lista.",
        "ayuda_patrones": "Atributos aceptados (p. ej. Authorize, AllowAnonymous, ValidateAntiForgeryToken).",
        "parametros": {
            "alcance": {"tipo": "opcion", "opciones": ["clase", "accion"], "defecto": "clase", "descripcion": "Revisar el controlador completo o cada acción que modifica datos."},
            "excluir_si": {"tipo": "lista", "defecto": [], "descripcion": "Omitir controladores que tengan alguno de estos atributos (p. ej. ApiController)."},
        },
    },
    "excepcion_mal_manejada": {
        "funcion": excepcion_mal_manejada, "archivos": "csharp",
        "nombre": "Excepción mal manejada",
        "descripcion": "Marca bloques catch vacíos y los que capturan excepciones genéricas sin registrarlas ni relanzarlas.",
        "ayuda_patrones": "Tipos de excepción considerados genéricos (p. ej. Exception, SystemException).",
        "parametros": {
            "llamadas_de_registro": {"tipo": "lista", "defecto": ["log", "logger", "trace"], "descripcion": "Fragmentos que identifican una llamada de registro."},
        },
    },
    "comparacion_texto_plano": {
        "funcion": comparacion_texto_plano, "archivos": "csharp",
        "nombre": "Comparación directa de valores sensibles",
        "descripcion": "Marca comparaciones con == o Equals de valores cuyo nombre contiene un patrón (p. ej. contraseñas sin hash).",
        "ayuda_patrones": "Palabras clave (p. ej. password, contrasena).",
        "parametros": {
            "excepto_si_contiene": {"tipo": "lista", "defecto": ["hash", "verify", "null"], "descripcion": "No marcar si la comparación menciona estas palabras."},
        },
    },
    "recurso_sin_liberar": {
        "funcion": recurso_sin_liberar, "archivos": "csharp",
        "nombre": "Recurso IDisposable sin liberar",
        "descripcion": "Marca objetos de los tipos de la lista creados sin 'using' ni llamada a Dispose()/Close().",
        "ayuda_patrones": "Tipos IDisposable (p. ej. SqlConnection, FileStream).",
        "parametros": {},
    },
    "variable_no_usada": {
        "funcion": variable_no_usada, "archivos": "csharp",
        "nombre": "Variable local sin uso",
        "descripcion": "Marca variables locales que se declaran y no vuelven a usarse.",
        "ayuda_patrones": "Nombres de variables a ignorar (opcional).",
        "parametros": {},
        "patrones_opcionales": True,
    },
    "nomenclatura": {
        "funcion": nomenclatura, "archivos": "csharp",
        "nombre": "Convención de nombres",
        "descripcion": "Marca nombres que no cumplen la expresión regular indicada en el primer patrón.",
        "ayuda_patrones": "Una expresión regular (p. ej. ^[A-Z][a-zA-Z0-9]*$ para PascalCase).",
        "parametros": {
            "tipos": {"tipo": "lista", "defecto": ["property"], "descripcion": "Qué declarar revisar: property, field, variable."},
            "modificador": {"tipo": "texto", "defecto": "public", "descripcion": "Solo declaraciones con este modificador (vacío = todas)."},
        },
    },
    "paquete_vulnerable": {
        "funcion": paquete_vulnerable, "archivos": "csproj",
        "nombre": "Dependencia vulnerable u obsoleta",
        "descripcion": "Revisa los paquetes NuGet del .csproj contra la lista de versiones vulnerables u obsoletas.",
        "ayuda_patrones": "Paquete (cualquier versión) o Paquete<versión (p. ej. Newtonsoft.Json<13.0.1).",
        "parametros": {
            "version_flotante": {"tipo": "booleano", "defecto": True, "descripcion": "Marcar también versiones con '*' o sin versión."},
        },
        "patrones_opcionales": True,
    },
    "configuracion_insegura": {
        "funcion": configuracion_insegura, "archivos": "config",
        "nombre": "Ajuste inseguro en appsettings.json",
        "descripcion": "Marca ajustes de configuración con valores inseguros.",
        "ayuda_patrones": "Formato Clave=valor; la clave usa ':' entre niveles y admite '*' (p. ej. AllowedHosts=*, DetailedErrors=true).",
        "parametros": {},
    },
    "secreto_en_configuracion": {
        "funcion": secreto_en_configuracion, "archivos": "config",
        "nombre": "Secreto en archivo de configuración",
        "descripcion": "Marca contraseñas, llaves o tokens escritos en appsettings.json.",
        "ayuda_patrones": "Palabras clave del nombre del ajuste (p. ej. password, secret, apikey).",
        "parametros": {
            "marcadores_en_valor": {"tipo": "lista", "defecto": ["password=", "pwd="], "descripcion": "Fragmentos del valor que delatan una contraseña (cadenas de conexión)."},
        },
    },
}

DETECTORES: dict[str, Callable[[ReglaDef, dict], Resultado]] = {k: v["funcion"] for k, v in PLANTILLAS.items()}


def aplica_a(tipo_deteccion: str, ast: dict) -> bool:
    """¿El detector revisa este tipo de archivo? (C#, .csproj o configuración)."""
    archivos = PLANTILLAS.get(tipo_deteccion, {}).get("archivos", "csharp")
    return ast.get("kind", "csharp") == archivos
