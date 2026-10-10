import { useEffect, useState } from "react";
import { FolderSearch, X } from "lucide-react";
import { listarReglas } from "../api/adminClient";

const SEVERITY_TEXT = {
  CRÍTICO: "text-red-700",
  ADVERTENCIA: "text-amber-700",
  BAJO: "text-stone-500",
};

/**
 * Antes de analizar, el desarrollador ve las reglas que se aplicarán:
 * TODAS vienen marcadas por defecto y puede quitar las que no quiera.
 */
export default function AnalyzeDialog({ onCancelar, onContinuar }) {
  const [reglas, setReglas] = useState(null);
  const [marcadas, setMarcadas] = useState(new Set());
  const [error, setError] = useState(null);

  useEffect(() => {
    listarReglas()
      .then((todas) => {
        const activas = todas.filter((r) => r.activa);
        setReglas(activas);
        setMarcadas(new Set(activas.map((r) => r.codigo)));
      })
      .catch((e) => setError(e.message));
  }, []);

  const toggle = (codigo) =>
    setMarcadas((prev) => {
      const s = new Set(prev);
      s.has(codigo) ? s.delete(codigo) : s.add(codigo);
      return s;
    });

  const todas = reglas && marcadas.size === reglas.length;
  const toggleTodas = () => setMarcadas(todas ? new Set() : new Set(reglas.map((r) => r.codigo)));

  // Si están todas marcadas no se envía lista (el backend aplica todas las activas).
  const continuar = () => onContinuar(todas ? null : [...marcadas]);

  return (
    <div className="fixed inset-0 z-50 bg-stone-900/40 flex items-center justify-center px-4" onClick={onCancelar}>
      <div className="w-full max-w-lg bg-white rounded-lg border border-stone-200 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between px-5 py-4 border-b border-stone-200">
          <div>
            <p className="text-[14px] font-medium text-stone-900">Reglas a aplicar en el análisis</p>
            <p className="text-[12px] text-stone-500 mt-0.5">
              Todas vienen activadas. Puede quitar las que no necesite; el auditor elegirá después qué criterios evaluar.
            </p>
          </div>
          <button onClick={onCancelar} className="text-stone-400 hover:text-stone-700 ml-4" aria-label="Cerrar">
            <X size={16} />
          </button>
        </div>

        {error && <p className="px-5 py-3 text-[12.5px] text-red-700">{error}</p>}

        {reglas && (
          <div className="max-h-[50vh] overflow-y-auto">
            <label className="flex items-center gap-3 px-5 py-2.5 border-b border-stone-100 text-[12px] text-stone-600 cursor-pointer">
              <input type="checkbox" checked={todas} onChange={toggleTodas} className="accent-stone-900" />
              Seleccionar todas ({marcadas.size} de {reglas.length})
            </label>
            {reglas.map((r) => (
              <label key={r.codigo} className="flex items-center gap-3 px-5 py-2.5 hover:bg-stone-50 cursor-pointer">
                <input type="checkbox" checked={marcadas.has(r.codigo)} onChange={() => toggle(r.codigo)} className="accent-stone-900" />
                <span className="font-mono text-[12px] text-stone-500 w-16 shrink-0">{r.codigo}</span>
                <span className="flex-1 min-w-0">
                  <span className="block text-[13px] text-stone-800 truncate">{r.nombre}</span>
                  <span className="block text-[11px] text-stone-500">{r.modulo}</span>
                </span>
                <span className={`text-[11px] shrink-0 ${SEVERITY_TEXT[r.severidad]}`}>{r.severidad}</span>
              </label>
            ))}
          </div>
        )}

        <div className="flex justify-end gap-2 px-5 py-3 border-t border-stone-200">
          <button onClick={onCancelar} className="h-9 px-4 rounded-md text-[12.5px] text-stone-600 hover:bg-stone-100">
            Cancelar
          </button>
          <button
            onClick={continuar}
            disabled={!reglas || marcadas.size === 0}
            className="h-9 px-4 rounded-md bg-stone-900 text-white text-[12.5px] hover:bg-stone-800 disabled:opacity-50 flex items-center gap-2"
          >
            <FolderSearch size={14} /> Elegir carpeta y analizar
          </button>
        </div>
      </div>
    </div>
  );
}
