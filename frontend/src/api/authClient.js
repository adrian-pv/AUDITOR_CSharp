import { api } from "./http";

export const login = (correo, contrasena) =>
  api("/api/auth/login", { method: "POST", body: { correo, contrasena } });

export const obtenerYo = () => api("/api/auth/yo");

export const actualizarPerfil = (nombre) => api("/api/auth/yo", { method: "PATCH", body: { nombre } });

export const cambiarContrasena = (actual, nueva) =>
  api("/api/auth/yo/contrasena", { method: "POST", body: { actual, nueva } });
