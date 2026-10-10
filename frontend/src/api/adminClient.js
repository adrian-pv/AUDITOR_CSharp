import { api } from "./http";

// Usuarios (solo Administrador)
export const listarUsuarios = () => api("/api/usuarios");
export const crearUsuario = (datos) => api("/api/usuarios", { method: "POST", body: datos });
export const modificarUsuario = (id, cambios) =>
  api(`/api/usuarios/${id}`, { method: "PATCH", body: cambios });

// Reglas (todos las ven; solo el Administrador las activa/desactiva)
export const listarReglas = () => api("/api/reglas");
export const cambiarRegla = (codigo, activa) =>
  api(`/api/reglas/${codigo}`, { method: "PATCH", body: { activa } });
