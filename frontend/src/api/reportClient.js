import { api } from "./http";

/**
 * Reporte de muestra en /sample-data — generado ejecutando el motor real
 * contra un fixture de AST, no escrito a mano. Se muestra cuando el
 * usuario todavía no tiene ningún reporte en su historial.
 */
export async function fetchSampleReport() {
  const res = await fetch("/sample-data/report.sample.json");
  return res.json();
}

/**
 * Envía los archivos .cs de la carpeta elegida al backend, que corre el
 * motor real (Roslyn + las reglas elegidas; todas por defecto), guarda el reporte en la base de
 * datos a nombre del usuario con sesión, y lo devuelve.
 */
export async function analyzeFolder(files, reglas = null) {
  // Código C# más archivos de proyecto (.csproj: dependencias) y configuración (appsettings*.json).
  const esProyecto = (n) => n.endsWith(".csproj") || (n.startsWith("appsettings") && n.endsWith(".json"));
  const ignorada = (f) => /(^|\/)(bin|obj|node_modules|\.git|\.vs)\//.test(f.webkitRelativePath || "");
  const archivosCs = files.filter((f) => !ignorada(f) && (f.name.endsWith(".cs") || esProyecto(f.name.toLowerCase())));
  if (!archivosCs.some((f) => f.name.endsWith(".cs"))) {
    throw new Error("La carpeta seleccionada no contiene archivos .cs");
  }

  const form = new FormData();
  for (const file of archivosCs) {
    form.append("archivos", file, file.webkitRelativePath || file.name);
  }
  // Sin lista = todas las reglas activas (comportamiento por defecto del backend).
  if (reglas && reglas.length > 0) form.append("reglas", reglas.join(","));
  return api("/api/analizar", { method: "POST", form });
}

export const listarReportes = () => api("/api/reportes");
export const obtenerReporte = (reporteId) => api(`/api/reportes/${reporteId}`);
export const evaluarHallazgo = (hallazgoId, estado) =>
  api(`/api/hallazgos/${hallazgoId}`, { method: "PATCH", body: { estado } });

/** El auditor guarda qué reglas (criterios) evaluar en un reporte. */
export const guardarCriterios = (reporteId, evaluadas) =>
  api(`/api/reportes/${reporteId}/criterios`, { method: "PUT", body: { evaluadas } });

/** Reporte guardado como archivo .json: todos los hallazgos y criterios. */
export const exportarReporte = (reporteId) => api(`/api/reportes/${reporteId}/exportar`);

/**
 * Muestra el contenido de un .json de reporte (propio o de un tercero) sin
 * volver a analizar ni guardar nada. El backend lo valida y recalcula métricas.
 */
export const vistaDeArchivo = (documento) => api("/api/reportes/vista", { method: "POST", body: documento });

/** Nombre de archivo: reporte_<proyecto>_<AAAAMMDD_HHMMSS>.json */
export function nombreArchivoReporte(proyecto, fechaIso) {
  const f = fechaIso ? new Date(fechaIso) : new Date();
  const d = isNaN(f) ? new Date() : f;
  const p = (n) => String(n).padStart(2, "0");
  const sello = `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
  const limpio = (proyecto || "proyecto").replace(/[^A-Za-z0-9._-]+/g, "_").replace(/^_+|_+$/g, "") || "proyecto";
  return `reporte_${limpio}_${sello}.json`;
}

/** Descarga un objeto como archivo .json desde el navegador. */
export function descargarJson(objeto, nombre) {
  const blob = new Blob([JSON.stringify(objeto, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nombre;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
