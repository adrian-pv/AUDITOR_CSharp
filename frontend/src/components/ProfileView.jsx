import { useState } from "react";
import { actualizarPerfil, cambiarContrasena } from "../api/authClient";
import { useAuth } from "../auth/AuthContext";

const inputCls =
  "w-full h-9 rounded-md border border-stone-300 bg-white px-3 text-[13px] outline-none focus:border-stone-900 focus:ring-1 focus:ring-stone-900";

function Mensaje({ estado }) {
  if (!estado) return null;
  const ok = estado.tipo === "ok";
  return (
    <p key={estado.texto} className={`text-[12px] mt-3 ${ok ? "animate-fade-up text-emerald-700" : "animate-shake text-red-700"}`}>{estado.texto}</p>
  );
}

export default function ProfileView() {
  const { usuario, setUsuario } = useAuth();
  const [nombre, setNombre] = useState(usuario.nombre);
  const [estadoPerfil, setEstadoPerfil] = useState(null);

  const [actual, setActual] = useState("");
  const [nueva, setNueva] = useState("");
  const [confirmar, setConfirmar] = useState("");
  const [estadoClave, setEstadoClave] = useState(null);

  const guardarPerfil = async (e) => {
    e.preventDefault();
    try {
      setUsuario(await actualizarPerfil(nombre));
      setEstadoPerfil({ tipo: "ok", texto: "Perfil actualizado." });
    } catch (err) {
      setEstadoPerfil({ tipo: "error", texto: err.message });
    }
  };

  const guardarClave = async (e) => {
    e.preventDefault();
    if (nueva !== confirmar) {
      setEstadoClave({ tipo: "error", texto: "La nueva contraseña y su confirmación no coinciden." });
      return;
    }
    try {
      await cambiarContrasena(actual, nueva);
      setActual("");
      setNueva("");
      setConfirmar("");
      setEstadoClave({ tipo: "ok", texto: "Contraseña actualizada." });
    } catch (err) {
      setEstadoClave({ tipo: "error", texto: err.message });
    }
  };

  return (
    <div className="p-8 max-w-3xl space-y-6">
      <section className="border border-stone-200 rounded-lg bg-white">
        <div className="px-5 py-3 border-b border-stone-200 text-[13px] font-medium text-stone-900">
          Datos de la cuenta
        </div>
        <form onSubmit={guardarPerfil} className="p-5 grid sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-[12px] text-stone-600 mb-1.5">Nombre</label>
            <input className={inputCls} value={nombre} onChange={(e) => setNombre(e.target.value)} required minLength={2} />
          </div>
          <div>
            <label className="block text-[12px] text-stone-600 mb-1.5">Correo</label>
            <input className={`${inputCls} bg-stone-50 text-stone-500`} value={usuario.correo} disabled />
          </div>
          <div>
            <label className="block text-[12px] text-stone-600 mb-1.5">Rol</label>
            <input className={`${inputCls} bg-stone-50 text-stone-500`} value={usuario.rol} disabled />
          </div>
          <div className="sm:col-span-2">
            <button className="h-9 px-4 rounded-md bg-stone-900 text-white text-[12.5px] hover:bg-stone-800">
              Guardar cambios
            </button>
            <Mensaje estado={estadoPerfil} />
          </div>
        </form>
      </section>

      <section className="border border-stone-200 rounded-lg bg-white">
        <div className="px-5 py-3 border-b border-stone-200 text-[13px] font-medium text-stone-900">
          Cambiar contraseña
        </div>
        <form onSubmit={guardarClave} className="p-5 grid sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-[12px] text-stone-600 mb-1.5">Contraseña actual</label>
            <input type="password" autoComplete="current-password" className={inputCls} value={actual} onChange={(e) => setActual(e.target.value)} required />
          </div>
          <div>
            <label className="block text-[12px] text-stone-600 mb-1.5">Nueva (mín. 8 caracteres)</label>
            <input type="password" autoComplete="new-password" className={inputCls} value={nueva} onChange={(e) => setNueva(e.target.value)} required minLength={8} />
          </div>
          <div>
            <label className="block text-[12px] text-stone-600 mb-1.5">Confirmar nueva</label>
            <input type="password" autoComplete="new-password" className={inputCls} value={confirmar} onChange={(e) => setConfirmar(e.target.value)} required minLength={8} />
          </div>
          <div className="sm:col-span-3">
            <button className="h-9 px-4 rounded-md bg-stone-900 text-white text-[12.5px] hover:bg-stone-800">
              Actualizar contraseña
            </button>
            <Mensaje estado={estadoClave} />
          </div>
        </form>
      </section>
    </div>
  );
}
