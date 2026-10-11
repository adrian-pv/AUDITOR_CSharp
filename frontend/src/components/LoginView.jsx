import { useState } from "react";
import { Loader2, LockKeyhole } from "lucide-react";
import { useAuth } from "../auth/AuthContext";

export default function LoginView() {
  const { login, aviso } = useAuth();
  const [correo, setCorreo] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);
  const [intentos, setIntentos] = useState(0); // para repetir la animación en cada error

  const enviar = async (e) => {
    e.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      await login(correo, contrasena);
    } catch (err) {
      setError(err.message);
      setIntentos((n) => n + 1);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-stone-50">
      {/* Panel de marca */}
      <aside className="animate-fade-in hidden md:flex w-[42%] max-w-xl bg-stone-900 text-stone-100 flex-col justify-between p-10">
        <div>
          <p className="font-mono text-[15px] font-semibold">AUDITOR_C#</p>
          <p className="text-[12px] text-stone-400 mt-1">Gobierno &amp; auditoría continua</p>
        </div>
        <div className="space-y-5">
          <h2 className="text-2xl font-semibold leading-snug">
            Gobierno y auditoría de código fuente C#, automatizado en Python.
          </h2>
          <ul className="text-[13px] text-stone-400 space-y-2">
            <li>— Análisis sobre el árbol de sintaxis de Roslyn</li>
            <li>— Reglas de Seguridad, Rendimiento, Memoria y Gobierno</li>
            <li>— Historial de reportes por proyecto y por usuario</li>
          </ul>
        </div>
        <p className="text-[11px] text-stone-500">Acceso restringido a usuarios registrados.</p>
      </aside>

      {/* Formulario */}
      <main className="flex-1 flex items-center justify-center px-4 py-10">
        <form onSubmit={enviar} className="animate-fade-up w-full max-w-sm">
          <div className="md:hidden mb-8">
            <p className="font-mono text-[15px] font-semibold text-stone-900">AUDITOR_C#</p>
            <p className="text-[12px] text-stone-500 mt-0.5">Gobierno &amp; auditoría continua</p>
          </div>

          <div className="w-9 h-9 rounded-md bg-stone-900 text-white flex items-center justify-center mb-5">
            <LockKeyhole size={17} strokeWidth={1.75} />
          </div>
          <h1 className="text-xl font-semibold text-stone-900">Iniciar sesión</h1>
          <p className="text-[13px] text-stone-500 mt-1 mb-7">
            Ingrese con la cuenta que le asignó el administrador.
          </p>

          {(error || aviso) && (
            <div key={intentos} className="animate-shake mb-5 rounded-md border border-red-200 bg-red-50 px-3.5 py-2.5 text-[12.5px] text-red-700">
              {error || aviso}
            </div>
          )}

          <label className="block text-[12px] font-medium text-stone-700 mb-1.5" htmlFor="correo">
            Correo electrónico
          </label>
          <input
            id="correo"
            type="email"
            autoComplete="username"
            required
            autoFocus
            value={correo}
            onChange={(e) => setCorreo(e.target.value)}
            className="w-full h-10 rounded-md border border-stone-300 bg-white px-3 text-[13.5px] outline-none focus:border-stone-900 focus:ring-1 focus:ring-stone-900"
            placeholder="usuario@empresa.com"
          />

          <label className="block text-[12px] font-medium text-stone-700 mb-1.5 mt-4" htmlFor="contrasena">
            Contraseña
          </label>
          <input
            id="contrasena"
            type="password"
            autoComplete="current-password"
            required
            value={contrasena}
            onChange={(e) => setContrasena(e.target.value)}
            className="w-full h-10 rounded-md border border-stone-300 bg-white px-3 text-[13.5px] outline-none focus:border-stone-900 focus:ring-1 focus:ring-stone-900"
          />

          <button
            type="submit"
            disabled={enviando}
            className="btn-press mt-6 w-full h-10 rounded-md bg-stone-900 text-white text-[13.5px] font-medium hover:bg-stone-800 transition-colors disabled:opacity-60 flex items-center justify-center gap-2"
          >
            {enviando && <Loader2 size={15} className="animate-spin" />}
            {enviando ? "Verificando…" : "Iniciar sesión"}
          </button>
        </form>
      </main>
    </div>
  );
}
