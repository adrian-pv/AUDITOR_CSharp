# AUDITOR_C# — Herramienta de Gobierno y Auditoría de Código Fuente C#

Estructura base del proyecto descrito en el documento de graduación
(automatización en Python de reglas heurísticas sobre el AST de Roslyn,
organizadas en cuatro módulos: Seguridad, Rendimiento, Memoria y Gobierno
de Código).

Este scaffold reemplaza las capturas provisionales de los Anexos: la
interfaz ya no es una imagen estática, es una aplicación real conectada a
un motor de reglas que sí se ejecuta y sí se prueba (ver `backend/tests`).

## Estructura

```
auditor-csharp-tool/
├── backend/            Motor de reglas en Python
│   ├── engine/          Orquestador, puente a Roslyn, clases base, reporte
│   ├── modules/          Catálogo de reglas de fábrica por módulo (seguridad, rendimiento, memoria, gobierno)
│   ├── api/              Endpoints HTTP: autenticación, usuarios, reglas, análisis/reportes
│   ├── autenticacion/    Hash de contraseñas (scrypt) y sesiones con JWT
│   ├── persistencia/     Base de datos: Usuario, Proyecto, Reporte, Hallazgo, Regla
│   ├── server.py         Servidor API (FastAPI)
│   ├── tests/            Pruebas unitarias + fixture de AST de ejemplo
│   └── main.py           CLI: `python main.py <ruta-solucion> --out reporte.json`
├── roslyn-bridge/      Puente en C#/.NET que expone el AST de Roslyn como JSON
├── frontend/           Interfaz web (React + Vite + Tailwind)
│   ├── src/auth/         Sesión del usuario (AuthContext)
│   ├── src/components/   Login, Panel General, Analizador, Historial, Reglas, Usuarios, Mi perfil
│   └── sample-data/      report.sample.json — generado por el motor real, no escrito a mano
└── docs/
    └── arquitectura.md  Cómo cada carpeta corresponde a las secciones del documento
```

## Cómo se conectan las piezas

1. **`roslyn-bridge`** parsea los `.cs` de la solución auditada y produce un
   AST simplificado en JSON (ver el esquema documentado en
   `backend/engine/ast_bridge.py`).
2. **`backend/modules/*`** contiene las reglas heurísticas; cada regla
   recibe ese AST y retorna una lista de hallazgos.
3. **`backend/engine/orchestrator.py`** corre todas las reglas activas,
   agrega las métricas (LOC, densidad de errores, score de gobierno,
   cumplimiento por módulo) y arma el reporte final.
4. **`frontend`** consume ese reporte (`report.sample.json` durante
   desarrollo, o el endpoint del backend en producción) y lo presenta en
   tres vistas: Panel General, Analizador y Reglas y Políticas.

## Puesta en marcha

### Backend — motor de reglas y servidor API

```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/ -v        # corre el motor contra el fixture de ejemplo
python server.py                  # levanta el servidor en http://127.0.0.1:8000
```

La base de datos es **PostgreSQL**. Antes de arrancar el servidor, copie
`backend/.env.example` como `backend/.env` y escriba ahí la cadena de
conexión (`AUDITOR_DB_URL=postgresql://...`). El archivo `.env` no se sube al
repositorio. Luego cree las tablas una sola vez:

```bash
python crear_bd.py      # ejecuta backend/sql/esquema_postgresql.sql (solo crea lo que falte)
```

(si las tablas no existen, `server.py` también las crea por sí solo).

La primera vez que arranca, `server.py` carga el catálogo de reglas y crea un
**Administrador inicial**, y lo muestra en consola:

```
correo:     admin@auditor.local
contraseña: admin123
```

Inicie sesión con esa cuenta, cambie la contraseña en **Mi perfil** y cree
los demás usuarios en **Usuarios**. Sin `backend/.env` el servidor usa un archivo SQLite local
(`backend/data/`), pensado solo para pruebas.

Variables de entorno opcionales:

| Variable | Para qué |
|---|---|
| `AUDITOR_DB_URL` | Cadena de conexión de PostgreSQL (en `backend/.env`) |
| `AUDITOR_ADMIN_PASSWORD` | Contraseña del Administrador inicial |
| `AUDITOR_SECRET` | Clave para firmar las sesiones (si no, se genera en `backend/data/.secret`) |

Documentación interactiva de la API: http://127.0.0.1:8000/docs

### Usuarios y roles

| Rol | Qué puede hacer |
|---|---|
| **Administrador** | Gestiona usuarios y activa/desactiva reglas; también puede analizar y evaluar |
| **Desarrollador** | Analiza carpetas de código (todas las reglas activas por defecto; puede quitar algunas antes de analizar); ve solo su propio historial |
| **Auditor** | No ejecuta análisis: revisa los reportes de todos los desarrolladores, elige qué reglas (criterios) evaluar en cada reporte —el panel y el score se recalculan y la selección queda guardada— y evalúa cada hallazgo (Pendiente / Solucionado / Fallido) |

Cada reporte guardado (en la base de datos y como `.json`) solo lleva el
`usuario_id` de quien lo generó y un `reporte_id` único, junto con la fecha y
hora — no datos personales.

`server.py` es lo que conecta el frontend con el motor real: recibe los
archivos `.cs` que el usuario elige desde el navegador, los analiza con
`roslyn-bridge` + las reglas de `backend/modules/`, y devuelve el reporte.
Déjalo corriendo en su propia terminal mientras usas la interfaz.

### Puente Roslyn (requiere SDK de .NET 10)

```bash
cd roslyn-bridge
dotnet build -c Release
```

Sin este paso, `server.py` sigue levantando pero el botón "Analizar
carpeta…" del frontend devolverá el error "RoslynBridge.dll no compilado".

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Al abrir la interfaz aparece la pantalla de inicio de sesión. Después de
entrar verás tu reporte más reciente, o el reporte de muestra si todavía no
tienes ninguno. El botón **"Analizar carpeta…"** de la
cabecera abre el explorador de archivos de Windows para elegir una
carpeta con código C#; al seleccionarla, el frontend se la envía al
backend, corre el motor real, y reemplaza la vista con esos hallazgos
(etiqueta "<proyecto> · <fecha y hora> · <usuario>") y lo guarda en el
**Historial**.

Cada análisis real que corres desde la interfaz también se guarda en
`backend/reports/`, con nombre `reporte_<nombre-carpeta>_<AAAAMMDD_HHMMSS>.json`
— así queda un historial de cada corrida sin que se sobrescriban entre sí.

### Veredicto para producción

Cada reporte muestra un veredicto calculado con los hallazgos de los criterios
evaluados (todos cuentan, sin importar su estado):

- **Aprobado** (verde): sin hallazgos.
- **Aprobado con advertencias** (amarillo): solo advertencias o hallazgos de
  severidad baja; conviene revisarlos, pero no impiden el paso a producción.
- **No aprobado** (rojo): al menos un hallazgo crítico; se listan las reglas
  que lo impiden.

El veredicto aparece en el Panel General, en el Historial, en el `.json`
descargado y al final de la salida de `python main.py`.

### Descargar y cargar reportes `.json`

- **"Descargar .json"** (cabecera, en Panel General y Analizador) guarda el
  reporte abierto como archivo: todos los hallazgos con su estado y los
  criterios, indicando cuáles evaluó el auditor (`"formato": "AUDITOR_CSharp/reporte"`,
  `"version": 1`).
- **"Cargar .json"** abre un reporte desde un archivo (por ejemplo, el de un
  tercero) **sin volver a analizar el código ni guardarlo en la base de datos**
  (etiqueta azul "Archivo .json · … · sin guardar"). El auditor puede cambiar
  criterios y estados de los hallazgos y volver a descargarlo con esos cambios.
- El archivo cargado no se considera confiable: el backend lo valida
  (`POST /api/reportes/vista`) y **recalcula las métricas** a partir de los
  hallazgos, sin usar las que traiga el archivo. También se aceptan los `.json`
  antiguos de `backend/reports/`.

## Reglas configurables y cobertura OWASP

Las reglas **no están programadas una por una**: cada regla de la tabla
`regla` elige uno de los detectores genéricos del motor
(`backend/engine/detectores.py`) y le indica qué buscar con una lista de
**patrones** (palabras clave, métodos, tipos, caracteres especiales, pares
`Miembro=valor`, paquetes NuGet…). El **Administrador** puede, desde
*Reglas y Políticas*:

- editar los patrones, la severidad, las categorías OWASP/CWE y los textos de cualquier regla;
- crear reglas nuevas eligiendo una plantilla (tipo de detección), sin programar;
- activarlas o desactivarlas.

Ejemplo: si aparece un carácter especial nuevo capaz de romper una consulta,
basta con agregarlo a los patrones de **SEG-004** y el siguiente análisis ya
lo detecta.

Además del código C#, el análisis revisa los `.csproj` (dependencias NuGet) y
los `appsettings*.json` (configuración). Catálogo de fábrica
(`backend/modules/*/reglas.py`), que cubre las diez categorías del OWASP Top
10:2021 y las diez de la edición 2025:

| Código | Regla | OWASP 2021 | OWASP 2025 | CWE |
|---|---|---|---|---|
| SEG-001 | Credenciales embebidas en el código | A07:2021 | A07:2025 | CWE-798 |
| SEG-002 | Inyección SQL: consulta sin parametrizar | A03:2021 | A05:2025 | CWE-89 |
| SEG-003 | Inyección de comandos del sistema operativo | A03:2021 | A05:2025 | CWE-78 |
| SEG-004 | Caracteres especiales peligrosos junto a datos externos | A03:2021 | A05:2025 | CWE-74 |
| SEG-005 | Recorrido de directorios (Path Traversal) | A01:2021 | A01:2025 | CWE-22 |
| SEG-006 | Solicitud a URL controlada por el usuario (SSRF) | A10:2021 | A01:2025 | CWE-918 |
| SEG-007 | Algoritmo criptográfico débil u obsoleto | A02:2021 | A04:2025 | CWE-327 |
| SEG-008 | Generador de números aleatorios no criptográfico | A02:2021 | A04:2025 | CWE-330 |
| SEG-009 | Deserialización insegura | A08:2021 | A08:2025 | CWE-502 |
| SEG-010 | Validación de tokens JWT desactivada | A07:2021 | A07:2025 | CWE-287 |
| SEG-011 | Configuración de seguridad desactivada en el código | A05:2021 | A02:2025 | CWE-16 |
| SEG-012 | Deserialización JSON con tipos arbitrarios | A08:2021 | A08:2025 | CWE-502 |
| SEG-013 | Política CORS abierta a cualquier origen | A05:2021 | A02:2025 | CWE-942 |
| SEG-014 | Controlador sin control de acceso | A01:2021 | A01:2025 | CWE-862 |
| SEG-015 | Acción que modifica datos sin protección CSRF | A01:2021 | A01:2025 | CWE-352 |
| SEG-016 | Excepción ignorada o capturada de forma genérica | A09:2021 | A10:2025 | CWE-390 |
| SEG-017 | Datos sensibles escritos en el registro (log) | A09:2021 | A09:2025 | CWE-532 |
| SEG-018 | Dependencia vulnerable, obsoleta o sin versión fija | A06:2021 | A03:2025 | CWE-1104 |
| SEG-019 | Configuración insegura en appsettings.json | A05:2021 | A02:2025 | CWE-16 |
| SEG-020 | Secreto en archivo de configuración | A07:2021 | A07:2025 | CWE-798 |
| SEG-021 | Contraseña comparada en texto plano | A04:2021 | A06:2025 | CWE-256 |
| PERF-001 | Variables locales declaradas sin utilización | — | — | CWE-563 |
| MEM-004 | Clases IDisposable sin bloque 'using' o cierre formal | — | A10:2025 | CWE-404 |
| GOV-001 | Falta de nomenclatura estándar PascalCase | — | — | — |

`backend/tests/fixtures/AtuneraPacifico/` es un proyecto C# de muestra con un
caso de cada regla (y código seguro que no debe marcarse); las pruebas
verifican que cada regla lo detecta.

## Estado actual

- 24 reglas de fábrica en los cuatro módulos, con cobertura completa del
  OWASP Top 10:2021 y 2025, validadas de punta a punta con Roslyn sobre el
  proyecto de muestra (ver `docs/arquitectura.md` para las limitaciones del
  análisis puramente sintáctico).
- Reglas editables y creables por el Administrador desde la interfaz.
