# Trazabilidad arquitectura ↔ documento

| Carpeta / archivo | Corresponde a |
|---|---|
| `roslyn-bridge/` | Uso de la interfaz de programación Roslyn para construir el AST (Cap. II, Tecnologías; Supuesto 4) |
| `backend/modules/seguridad/reglas.py` | Catálogo de reglas de Seguridad, OWASP Top 10:2021 y 2025 — Módulo 1 |
| `backend/modules/rendimiento/reglas.py` | Reglas de Rendimiento (.NET) — Módulo 2 |
| `backend/modules/memoria/reglas.py` | Reglas de Gestión de Memoria — Módulo 3 |
| `backend/modules/gobierno/reglas.py` | Reglas de Gobierno Estructural — Módulo 4 |
| `backend/engine/detectores.py` | Detectores genéricos (plantillas) que interpretan los patrones de cada regla |
| `frontend/src/components/RuleEditor.jsx` | Administración de reglas: edición de patrones y creación de reglas nuevas |
| `backend/engine/orchestrator.py` | Cálculo de densidad de errores y score de gobierno (Anexo A1, panel general) |
| `frontend/src/components/RulesView.jsx` | Matriz de reglas y cobertura OWASP Top 10 (Anexo A3) |
| `backend/engine/orchestrator.py` (`calcular_veredicto`), `frontend/src/components/VeredictoBanner.jsx` | Filtro previo a producción: veredicto Aprobado / Aprobado con advertencias / No aprobado según la severidad de los hallazgos |
| `backend/persistencia/modelos.py`, `backend/sql/esquema_postgresql.sql` | Modelo Entidad-Relación (Cap. V, Figuras 12 y 13): usuario, proyecto, reporte, hallazgo, regla en PostgreSQL |
| `backend/autenticacion/` | Inicio de sesión y control de acceso por rol (Administrador, Desarrollador, Auditor — Cap. IV, 4.2) |
| `backend/api/` | Casos de uso del Cap. V expuestos como endpoints HTTP |
| `frontend/src/components/LoginView.jsx` | Pantalla de inicio de sesión (Figura de interfaz pendiente del Cap. V) |
| `backend/api/archivo_reporte.py` | Formato del reporte `.json` (descargar / cargar sin guardar); valida el archivo y recalcula las métricas |
| `backend/tests/` | Validación del motor sin depender del SDK de .NET instalado, para reproducibilidad en cualquier entorno de desarrollo |

## Próximos pasos sugeridos

1. ~~Exponer el motor como endpoint HTTP~~ — hecho (`server.py`).
2. ~~Inicio de sesión, roles y base de datos~~ — hecho.
3. ~~Cobertura OWASP Top 10 (2021 y 2025) y reglas editables por el Administrador~~ — hecho.
4. ~~Descargar el reporte como `.json` y cargar un `.json` de un tercero sin
   volver a analizarlo ni guardarlo en la base de datos~~ — hecho
   (`backend/api/archivo_reporte.py`).
5. Construir una `Compilation` con `SemanticModel` para resolver tipos y
   flujo de datos entre métodos (ver limitaciones).

## Limitaciones conocidas del puente (análisis puramente sintáctico)

`roslyn-bridge` NO usa un modelo semántico (`SemanticModel`/`Compilation`
con referencias resueltas) — solo recorre el árbol de sintaxis. Esto es
más simple de mantener pero tiene límites reales, encontrados al probar
con código real:

- **Reglas de "llamada con datos dinámicos" (SEG-002, 003, 005, 006):**
  rastrean la concatenación un solo nivel hacia atrás (variable declarada en
  el mismo método). Si la variable se reasigna o la cadena se arma en otro
  método, no se detecta.
- **Coincidencia por nombre:** sin modelo semántico, `MD5.Create` o
  `SqlCommand` se reconocen por su nombre en el código, no por su tipo
  resuelto; un alias o un tipo propio con el mismo nombre puede dar falsos
  positivos o negativos.
- **A04 / A06 (diseño inseguro):** el análisis estático solo puede
  aproximarlos con heurísticas (p. ej. SEG-021, contraseña comparada en texto
  plano); la mayoría de fallas de diseño requieren revisión humana.
- **MEM-004 (IDisposable):** cuando se declara con `var`, se resuelve el
  tipo mirando el `new Tipo(...)` del inicializador. Si la variable no se
  inicializa con `new` directamente (p. ej. viene de una fábrica o un
  método), no se puede resolver el tipo y la regla no se dispara.
- **PERF-001 y `disposed_explicitly`:** se calculan buscando el nombre de la
  variable en el mismo bloque (no con `DataFlowAnalysis`).

Para eliminar estas limitaciones habría que construir una `Compilation`
real con las referencias del proyecto y usar su `SemanticModel`, lo cual
implica resolver todas las dependencias del código auditado (no solo
parsear texto). Queda documentado como el siguiente paso natural del
motor, no como algo ya resuelto.
