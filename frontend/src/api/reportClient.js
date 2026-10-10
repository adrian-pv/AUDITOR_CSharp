/**
 * Carga inicial: siempre el reporte de muestra en /sample-data —
 * generado ejecutando el motor real contra un fixture de AST, no escrito
 * a mano. Sirve para ver la interfaz sin tener que analizar nada primero.
 */
export async function fetchSampleReport() {
  const res = await fetch("/sample-data/report.sample.json");
  return res.json();
}

/**
 * Envía los archivos .cs seleccionados en el navegador al backend
 * (backend/server.py) para que corra el motor real (Roslyn + reglas)
 * sobre ellos, y devuelve el reporte resultante.
 *
 * Requiere que `python server.py` esté corriendo en backend/ — si no,
 * lanza un error explicativo que la interfaz muestra directamente.
 */
export async function analyzeFolder(files) {
  const archivosCs = files.filter((f) => f.name.endsWith(".cs"));

  if (archivosCs.length === 0) {
    throw new Error("La carpeta seleccionada no contiene archivos .cs");
  }

  const formData = new FormData();
  for (const file of archivosCs) {
    formData.append("archivos", file, file.webkitRelativePath || file.name);
  }

  let res;
  try {
    res = await fetch("/api/analizar", { method: "POST", body: formData });
  } catch {
    throw new Error(
      "No se pudo conectar con el backend. ¿Está corriendo 'python server.py' en la carpeta backend/?"
    );
  }

  if (!res.ok) {
    throw new Error(`El servidor respondió con error ${res.status}`);
  }

  const data = await res.json();
  if (data.error) throw new Error(data.error);
  return data;
}
