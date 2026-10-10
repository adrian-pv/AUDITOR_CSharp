import { useEffect, useState } from "react";
import { cambiarRegla, listarReglas } from "../api/adminClient";
import { useAuth } from "../auth/AuthContext";

const SEVERITY_TEXT = {
  CRÍTICO: "text-red-700",
  ADVERTENCIA: "text-amber-700",
  BAJO: "text-stone-500",
};

export default function RulesView() {
  const { esAdmin } = useAuth();
  const [gatekeeper, setGatekeeper] = useState(true);
  const [reglas, setReglas] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    listarReglas().then(setReglas).catch((e) => setError(e.message));
  }, []);

  const toggleRegla = async (regla) => {
    setError(null);
    try {
      const actualizada = await cambiarRegla(regla.codigo, !regla.activa);
      setReglas((prev) => prev.map((r) => (r.codigo === actualizada.codigo ? actualizada : r)));
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="p-8 max-w-5xl space-y-6">
      <div className="border border-stone-200 rounded-lg bg-white p-4 flex items-center justify-between">
        <div>
          <p className="text-[13px] font-medium text-stone-900">Gatekeeper de gobierno de código</p>
          <p className="text-[12px] text-stone-500 mt-0.5">
            Bloquea el commit o despliegue si la densidad de errores supera el umbral configurado.
          </p>
        </div>
        <button
          onClick={() => setGatekeeper((v) => !v)}
          className={`shrink-0 w-10 h-6 rounded-full relative transition-colors ${
            gatekeeper ? "bg-stone-900" : "bg-stone-300"
          }`}
        >
          <span
            className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-all ${
              gatekeeper ? "left-[19px]" : "left-0.5"
            }`}
          />
        </button>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-2.5 text-[12.5px] text-red-700">{error}</div>
      )}

      <div className="border border-stone-200 rounded-lg bg-white divide-y divide-stone-200">
        <div className="px-4 py-3 flex items-baseline justify-between">
          <span className="text-[13px] font-medium text-stone-900">Matriz de reglas (.NET / C#)</span>
          <span className="text-[11px] text-stone-500">
            {esAdmin
              ? "Catálogo general: las reglas inactivas no se ofrecen en los análisis."
              : "Solo el Administrador puede activar o desactivar reglas."}
          </span>
        </div>
        {reglas.map((r) => (
          <div key={r.codigo} className="flex items-center gap-4 px-4 py-3">
            <span className="font-mono text-[12px] text-stone-500 w-16 shrink-0">{r.codigo}</span>
            <div className="flex-1 min-w-0">
              <p className="text-[13px] text-stone-800 truncate">{r.nombre}</p>
              <p className="text-[11px] text-stone-500">{r.modulo}</p>
            </div>
            <span className={`text-[11px] w-20 shrink-0 ${SEVERITY_TEXT[r.severidad]}`}>{r.severidad}</span>
            <button
              onClick={() => toggleRegla(r)}
              disabled={!esAdmin}
              className={`text-[12px] shrink-0 w-16 text-right disabled:cursor-default ${
                r.activa ? "text-emerald-700" : "text-stone-400"
              }`}
            >
              {r.activa ? "Activa" : "Inactiva"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
