import { useEffect, useState } from "react";
import { FolderSearch, X } from "lucide-react";
import { listarReglas } from "../api/adminClient";
import Modal from "../ui/Modal";
import Switch from "../ui/Switch";

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
    <Modal onCerrar={onCancelar}>
      <div className="w-full bg-white rounded-lg border border-stone-200 shadow-xl">
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
            <div className="flex items-center gap-3 px-5 py-2.5 border-b border-stone-100 text-[12px] text-stone-600">
              <Switch checked={todas} onChange={toggleTodas} tamano="sm" etiqueta="Seleccionar todas" />
              Todas las reglas ({marcadas.size} de {reglas.length})
            </div>
            {reglas.map((r) => (
              <div
                key={r.codigo}
                onClick={() => toggle(r.codigo)}
                className={`flex items-center gap-3 px-5 py-2.5 cursor-pointer transition-colors hover:bg-stone-50 ${marcadas.has(r.codigo) ? "" : "opacity-60"}`}
              >
                <span onClick={(e) => e.stopPropagation()}>
                  <Switch checked={marcadas.has(r.codigo)} onChange={() => toggle(r.codigo)} tamano="sm" etiqueta={r.codigo} />
                </span>
                <span className="font-mono text-[12px] text-stone-500 w-16 shrink-0">{r.codigo}</span>
                <span className="flex-1 min-w-0">
                  <span className="block text-[13px] text-stone-800 truncate">{r.nombre}</span>
                  <span className="block text-[11px] text-stone-500">{r.modulo}</span>
                </span>
                <span className={`text-[11px] shrink-0 ${SEVERITY_TEXT[r.severidad]}`}>{r.severidad}</span>
              </div>
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
            className="btn-press h-9 px-4 rounded-md bg-stone-900 text-white text-[12.5px] hover:bg-stone-800 transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            <FolderSearch size={14} /> Elegir carpeta y analizar
          </button>
        </div>
      </div>
    </Modal>
  );
}
