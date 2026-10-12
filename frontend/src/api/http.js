/**
 * Cliente HTTP común: agrega el token de sesión a cada petición y
 * traduce los errores del backend a mensajes legibles.
 */

const CLAVE_TOKEN = "auditor_token";
let alExpirarSesion = () => {};

export function getToken() {
  try {
    return localStorage.getItem(CLAVE_TOKEN);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(CLAVE_TOKEN, token);
    else localStorage.removeItem(CLAVE_TOKEN);
  } catch {
    /* almacenamiento no disponible: la sesión dura lo que la pestaña */
  }
}

/** AuthContext registra aquí qué hacer cuando el backend responde 401. */
export function onSesionExpirada(fn) {
  alExpirarSesion = fn;
}

export async function api(ruta, { method = "GET", body, form } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let res;
  try {
    res = await fetch(ruta, {
      method,
      headers,
      body: form ?? (body !== undefined ? JSON.stringify(body) : undefined),
    });
  } catch {
    throw new Error(
      "No se pudo conectar con el backend. ¿Está corriendo 'python server.py' en la carpeta backend/?"
    );
  }

  if (res.status === 401 && token) {
    alExpirarSesion();
  }
  if (res.status === 204) return null;

  let data = null;
  try {
    data = await res.json();
  } catch {
    /* respuesta sin cuerpo JSON */
  }

  // "Not Found" sin más detalle = la ruta no existe en el backend que está corriendo
  // (normalmente porque se actualizó el código y no se reinició python server.py).
  if (res.status === 404 && data?.detail === "Not Found") {
    throw new Error(
      "El backend no tiene esta función. Reinicie el servidor (Ctrl + C y 'python server.py' en la carpeta backend/) para cargar los cambios."
    );
  }
  if (!res.ok) {
    throw new Error(mensajeDeError(data) || `El servidor respondió con error ${res.status}`);
  }
  if (data && data.error) throw new Error(data.error);
  return data;
}

function mensajeDeError(data) {
  if (!data?.detail) return null;
  if (typeof data.detail === "string") return data.detail;
  // Errores de validación de FastAPI: lista de {loc, msg}
  if (Array.isArray(data.detail)) {
    return data.detail
      .map((d) => {
        const campo = d.loc?.[d.loc.length - 1];
        // Reglas propias del backend: el texto ya está en español.
        if (d.type === "value_error") return String(d.msg).replace(/^Value error, /, "");
        // Campo anidado (p. ej. en un .json cargado): hallazgos[3].severidad
        const ruta = (d.loc || [])
          .filter((p) => p !== "body")
          .map((p, i) => (typeof p === "number" ? `[${p}]` : i ? `.${p}` : p))
          .join("");
        // Mensajes de validación de Pydantic traducidos (p. ej. al cargar un .json de un tercero)
        const donde = ruta || campo;
        if (d.type === "literal_error") return `${donde}: valor no permitido (use ${String(d.ctx?.expected || "").replaceAll(" or ", " o ")}).`;
        if (d.type === "missing") return `${donde}: es obligatorio.`;
        if (d.type === "greater_than_equal") return `${donde}: debe ser mayor o igual a ${d.ctx?.ge}.`;
        if (d.type === "less_than_equal") return `${donde}: debe ser menor o igual a ${d.ctx?.le}.`;
        if (d.type === "int_parsing" || d.type === "int_type") return `${donde}: debe ser un número entero.`;
        if (d.type === "string_type") return `${donde}: debe ser texto.`;
        if (d.type === "list_type") return `${donde}: debe ser una lista.`;
        if (d.type === "bool_type" || d.type === "bool_parsing") return `${donde}: debe ser verdadero o falso.`;
        if (d.type === "string_too_long") return `${donde}: es demasiado largo (máx. ${d.ctx?.max_length}).`;
        if (d.type === "too_long") return `${donde}: tiene demasiados elementos.`;
        if (d.type === "string_too_short") return `'${campo}' es demasiado corto (mín. ${d.ctx?.min_length}).`;
        if (d.type === "string_pattern_mismatch") return `'${campo}' no tiene un formato válido.`;
        return `${ruta || campo}: ${d.msg}`;
      })
      .join(" ");
  }
  return null;
}
