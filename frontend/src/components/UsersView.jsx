import { useEffect, useState } from "react";
import { UserPlus } from "lucide-react";
import { crearUsuario, listarUsuarios, modificarUsuario } from "../api/adminClient";
import { useAuth } from "../auth/AuthContext";

const ROLES = ["Administrador", "Desarrollador", "Auditor"];
const DESCRIPCION_ROL = {
  Administrador: "Gestiona usuarios y reglas; puede analizar y evaluar.",
  Desarrollador: "Analiza sus proyectos y ve su propio historial.",
  Auditor: "Revisa los reportes de los desarrolladores y evalúa hallazgos.",
};

const inputCls =
  "w-full h-9 rounded-md border border-stone-300 bg-white px-3 text-[13px] outline-none focus:border-stone-900 focus:ring-1 focus:ring-stone-900";

const VACIO = { nombre: "", correo: "", contrasena: "", rol: "Desarrollador" };

export default function UsersView() {
  const { usuario: yo } = useAuth();
  const [usuarios, setUsuarios] = useState([]);
  const [nuevo, setNuevo] = useState(VACIO);
  const [error, setError] = useState(null);
  const [ok, setOk] = useState(null);

  const cargar = () => listarUsuarios().then(setUsuarios).catch((e) => setError(e.message));
  useEffect(() => {
    cargar();
  }, []);

  const crear = async (e) => {
    e.preventDefault();
    setError(null);
    setOk(null);
    try {
      const u = await crearUsuario(nuevo);
      setNuevo(VACIO);
      setOk(`Usuario ${u.correo} creado como ${u.rol}.`);
      cargar();
    } catch (err) {
      setError(err.message);
    }
  };

  const cambiar = async (id, cambios) => {
    setError(null);
    setOk(null);
    try {
      await modificarUsuario(id, cambios);
      cargar();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="p-8 max-w-5xl space-y-6">
      <section className="border border-stone-200 rounded-lg bg-white">
        <div className="px-5 py-3 border-b border-stone-200 text-[13px] font-medium text-stone-900 flex items-center gap-2">
          <UserPlus size={14} /> Nuevo usuario
        </div>
        <form onSubmit={crear} className="p-5 grid sm:grid-cols-2 lg:grid-cols-4 gap-4 items-end">
          <div>
            <label className="block text-[12px] text-stone-600 mb-1.5">Nombre</label>
            <input className={inputCls} value={nuevo.nombre} onChange={(e) => setNuevo({ ...nuevo, nombre: e.target.value })} required minLength={2} />
          </div>
          <div>
            <label className="block text-[12px] text-stone-600 mb-1.5">Correo</label>
            <input type="email" className={inputCls} value={nuevo.correo} onChange={(e) => setNuevo({ ...nuevo, correo: e.target.value })} required />
          </div>
          <div>
            <label className="block text-[12px] text-stone-600 mb-1.5">Contraseña inicial</label>
            <input type="password" autoComplete="new-password" className={inputCls} value={nuevo.contrasena} onChange={(e) => setNuevo({ ...nuevo, contrasena: e.target.value })} required minLength={8} />
          </div>
          <div>
            <label className="block text-[12px] text-stone-600 mb-1.5">Rol</label>
            <select className={inputCls} value={nuevo.rol} onChange={(e) => setNuevo({ ...nuevo, rol: e.target.value })}>
              {ROLES.map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
          </div>
          <p className="text-[11.5px] text-stone-500 sm:col-span-2 lg:col-span-3">{DESCRIPCION_ROL[nuevo.rol]}</p>
          <button className="h-9 px-4 rounded-md bg-stone-900 text-white text-[12.5px] hover:bg-stone-800">
            Crear usuario
          </button>
        </form>
      </section>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-2.5 text-[12.5px] text-red-700">{error}</div>
      )}
      {ok && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-[12.5px] text-emerald-700">{ok}</div>
      )}

      <section className="border border-stone-200 rounded-lg bg-white overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead>
            <tr className="text-left text-[11px] text-stone-500 border-b border-stone-200">
              <th className="px-4 py-2.5 font-medium">Nombre</th>
              <th className="px-4 py-2.5 font-medium">Correo</th>
              <th className="px-4 py-2.5 font-medium">Rol</th>
              <th className="px-4 py-2.5 font-medium">Estado</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-200">
            {usuarios.map((u) => (
              <tr key={u.id}>
                <td className="px-4 py-2.5 text-stone-800">
                  {u.nombre}
                  {u.id === yo.id && <span className="ml-2 text-[10.5px] text-stone-400">(usted)</span>}
                </td>
                <td className="px-4 py-2.5 font-mono text-[12px] text-stone-600">{u.correo}</td>
                <td className="px-4 py-2.5">
                  <select
                    value={u.rol}
                    onChange={(e) => cambiar(u.id, { rol: e.target.value })}
                    className="h-8 rounded-md border border-stone-300 bg-white px-2 text-[12.5px]"
                  >
                    {ROLES.map((r) => (
                      <option key={r}>{r}</option>
                    ))}
                  </select>
                </td>
                <td className="px-4 py-2.5">
                  <button
                    onClick={() => cambiar(u.id, { activo: !u.activo })}
                    className={`text-[12px] ${u.activo ? "text-emerald-700" : "text-stone-400"}`}
                    title={u.activo ? "Clic para desactivar" : "Clic para activar"}
                  >
                    {u.activo ? "Activo" : "Inactivo"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
