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
│   ├── modules/          Una carpeta por módulo (seguridad, rendimiento, memoria, gobierno)
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

## Estado actual

- El motor de reglas y sus 5 reglas de ejemplo (una por módulo, más una
  segunda de Seguridad) están implementados y probados, y ya se validaron
  contra código C# real de punta a punta (ver `docs/arquitectura.md` para
  las limitaciones conocidas del análisis puramente sintáctico).
- El frontend ya está conectado al motor real a través de `server.py` y el
  selector de carpeta. Lo que todavía no está implementado —como PERF-001,
  que depende de `DataFlowAnalysis`— simplemente no aparece en los
  hallazgos de un análisis real; el catálogo completo de reglas y la
  Matriz de Reglas y Políticas de la interfaz siguen siendo estáticos
  hasta que se amplíen (ver "Próximos pasos" en `docs/arquitectura.md`).

