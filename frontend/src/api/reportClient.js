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
  const archivosCs = files.filter((f) => f.name.endsWith(".cs"));
  if (archivosCs.length === 0) {
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
