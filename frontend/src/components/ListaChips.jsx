import { useState } from "react";
import { Plus, X } from "lucide-react";

/** Lista editable de textos (patrones de una regla): Enter o "Agregar" para sumar, ✕ para quitar. */
export default function ListaChips({ valores, onChange, placeholder, deshabilitado }) {
  const [nuevo, setNuevo] = useState("");

  const agregar = () => {
    const v = nuevo;
    if (!v.trim() || valores.includes(v)) return setNuevo("");
    onChange([...valores, v]);
    setNuevo("");
  };

  return (
    <div className="rounded-md border border-stone-300 bg-white p-2">
      <div className="flex flex-wrap gap-1.5">
        {valores.length === 0 && <span className="text-[12px] text-stone-400 px-1 py-0.5">Sin elementos</span>}
        {valores.map((v) => (
          <span key={v} className="inline-flex items-center gap-1 rounded bg-stone-100 border border-stone-200 pl-2 pr-1 py-0.5 font-mono text-[12px] text-stone-800">
            {v === " " ? "␠" : v}
            {!deshabilitado && (
              <button type="button" onClick={() => onChange(valores.filter((x) => x !== v))} className="text-stone-400 hover:text-red-600" aria-label={`Quitar ${v}`}>
                <X size={12} />
              </button>
            )}
          </span>
        ))}
      </div>
      {!deshabilitado && (
        <div className="flex gap-2 mt-2">
          <input
            value={nuevo}
            onChange={(e) => setNuevo(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                agregar();
              }
            }}
            placeholder={placeholder}
            className="flex-1 h-8 rounded border border-stone-300 px-2 font-mono text-[12px] outline-none focus:border-stone-900"
          />
          <button type="button" onClick={agregar} className="h-8 px-2.5 rounded border border-stone-300 text-[12px] text-stone-700 hover:bg-stone-100 flex items-center gap-1">
            <Plus size={13} /> Agregar
          </button>
        </div>
      )}
    </div>
  );
}
