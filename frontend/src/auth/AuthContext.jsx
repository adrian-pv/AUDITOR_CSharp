import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { login as apiLogin, obtenerYo } from "../api/authClient";
import { getToken, onSesionExpirada, setToken } from "../api/http";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [aviso, setAviso] = useState(null);

  const logout = useCallback((mensaje = null) => {
    setToken(null);
    setUsuario(null);
    setAviso(mensaje);
  }, []);

  // Si el token guardado ya no es válido, vuelve a la pantalla de inicio de sesión.
  useEffect(() => {
    onSesionExpirada(() => logout("Su sesión expiró. Inicie sesión de nuevo."));
    if (!getToken()) {
      setCargando(false);
      return;
    }
    obtenerYo()
      .then(setUsuario)
      .catch(() => setToken(null))
      .finally(() => setCargando(false));
  }, [logout]);

  const login = async (correo, contrasena) => {
    const { token, usuario } = await apiLogin(correo, contrasena);
    setToken(token);
    setAviso(null);
    setUsuario(usuario);
  };

  const valor = {
    usuario,
    setUsuario,
    cargando,
    aviso,
    login,
    logout,
    esAdmin: usuario?.rol === "Administrador",
    puedeAnalizar: usuario?.rol === "Administrador" || usuario?.rol === "Desarrollador",
    puedeEvaluar: usuario?.rol === "Administrador" || usuario?.rol === "Auditor",
  };

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
