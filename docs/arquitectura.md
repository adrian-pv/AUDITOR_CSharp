# Trazabilidad arquitectura ↔ documento

| Carpeta / archivo | Corresponde a |
|---|---|
| `roslyn-bridge/` | Uso de la interfaz de programación Roslyn para construir el AST (Cap. II, Tecnologías; Supuesto 4) |
| `backend/modules/seguridad/` | Reglas de categoría Seguridad (OWASP) — Módulo 1 |
| `backend/modules/rendimiento/` | Reglas de categoría Rendimiento (.NET) — Módulo 2 |
| `backend/modules/memoria/` | Reglas de Gestión de Memoria — Módulo 3 |
| `backend/modules/gobierno/` | Reglas de Gobierno Estructural — Módulo 4 |
| `backend/engine/orchestrator.py` | Cálculo de densidad de errores y score de gobierno (Anexo A1, panel general) |
| `frontend/src/components/RulesView.jsx` | Filtro obligatorio de gobierno de código / Gatekeeper (Anexo A3) |
| `backend/persistencia/modelos.py`, `backend/sql/esquema_postgresql.sql` | Modelo Entidad-Relación (Cap. V, Figuras 12 y 13): usuario, proyecto, reporte, hallazgo, regla en PostgreSQL |
| `backend/autenticacion/` | Inicio de sesión y control de acceso por rol (Administrador, Desarrollador, Auditor — Cap. IV, 4.2) |
| `backend/api/` | Casos de uso del Cap. V expuestos como endpoints HTTP |
| `frontend/src/components/LoginView.jsx` | Pantalla de inicio de sesión (Figura de interfaz pendiente del Cap. V) |
| `backend/tests/` | Validación del motor sin depender del SDK de .NET instalado, para reproducibilidad en cualquier entorno de desarrollo |

## Próximos pasos sugeridos

1. Completar en `roslyn-bridge/Program.cs` los `TODO` pendientes (uso real
   de `DataFlowAnalysis` para variables no utilizadas, rastreo de llamadas
   a `.Dispose()`).
2. Ampliar `REGLAS_REGISTRADAS` en `backend/engine/orchestrator.py` hasta
   cubrir el catálogo completo de reglas heurísticas descrito en 3.4.
3. ~~Exponer el motor como endpoint HTTP~~ — hecho (`server.py`).
4. ~~Inicio de sesión, roles y base de datos~~ — hecho.
5. Descargar el reporte como `.json` y cargar un `.json` de un tercero sin
   volver a analizarlo ni guardarlo en la base de datos.

## Limitaciones conocidas del puente (análisis puramente sintáctico)

`roslyn-bridge` NO usa un modelo semántico (`SemanticModel`/`Compilation`
con referencias resueltas) — solo recorre el árbol de sintaxis. Esto es
más simple de mantener pero tiene límites reales, encontrados al probar
con código real:

- **SEG-002 (inyección SQL):** rastrea la concatenación un solo nivel
  hacia atrás (variable declarada en el mismo método). Si la variable se
  reasigna, viene de un parámetro, o la concatenación ocurre en otro
  método, no se detecta.
- **MEM-004 (IDisposable):** cuando se declara con `var`, se resuelve el
  tipo mirando el `new Tipo(...)` del inicializador. Si la variable no se
  inicializa con `new` directamente (p. ej. viene de una fábrica o un
  método), no se puede resolver el tipo y la regla no se dispara.
- **`disposed_explicitly` siempre es `false`:** no se rastrea si en algún
  punto posterior del bloque se llama a `.Dispose()` manualmente.

Para eliminar estas limitaciones habría que construir una `Compilation`
real con las referencias del proyecto y usar su `SemanticModel`, lo cual
implica resolver todas las dependencias del código auditado (no solo
parsear texto). Queda documentado como el siguiente paso natural del
motor, no como algo ya resuelto.
