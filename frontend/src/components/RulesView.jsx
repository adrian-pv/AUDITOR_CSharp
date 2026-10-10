import { useState } from "react";

const REGLAS_INICIALES = [
  { codigo: "SEG-001", nombre: "Hardcoded Credentials (CWE-259)", modulo: "Módulo 1: Seguridad", severidad: "CRÍTICO", activa: true },
  { codigo: "SEG-002", nombre: "Inyección SQL sin parametrizar", modulo: "Módulo 1: Seguridad", severidad: "CRÍTICO", activa: true },
  { codigo: "PERF-001", nombre: "Variables locales sin utilización", modulo: "Módulo 2: Rendimiento", severidad: "ADVERTENCIA", activa: true },
  { codigo: "MEM-004", nombre: "IDisposable sin 'using' o cierre formal", modulo: "Módulo 3: Memoria", severidad: "ADVERTENCIA", activa: true },
  { codigo: "GOV-001", nombre: "Nomenclatura fuera de PascalCase", modulo: "Módulo 4: Gobierno", severidad: "BAJO", activa: true },
];

const SEVERITY_TEXT = {
  CRÍTICO: "text-red-700",
  ADVERTENCIA: "text-amber-700",
  BAJO: "text-stone-500",
};

export default function RulesView() {
  const [gatekeeper, setGatekeeper] = useState(true);
  const [reglas, setReglas] = useState(REGLAS_INICIALES);

  const toggleRegla = (codigo) =>
    setReglas((prev) =>
      prev.map((r) => (r.codigo === codigo ? { ...r, activa: !r.activa } : r))
    );

  return (
    <div className="p-8 max-w-5xl space-y-6">
      <div className="border border-stone-200 rounded-lg bg-white p-4 flex items-center justify-between">
        <div>
          <p className="text-[13px] font-medium text-stone-900">
            Gatekeeper de gobierno de código
          </p>
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

      <div className="border border-stone-200 rounded-lg bg-white divide-y divide-stone-200">
        <div className="px-4 py-3 text-[13px] font-medium text-stone-900">
          Matriz de reglas (.NET / C#)
        </div>
        {reglas.map((r) => (
          <div key={r.codigo} className="flex items-center gap-4 px-4 py-3">
            <span className="font-mono text-[12px] text-stone-500 w-16 shrink-0">{r.codigo}</span>
            <div className="flex-1 min-w-0">
              <p className="text-[13px] text-stone-800 truncate">{r.nombre}</p>
              <p className="text-[11px] text-stone-500">{r.modulo}</p>
            </div>
            <span className={`text-[11px] w-20 shrink-0 ${SEVERITY_TEXT[r.severidad]}`}>
              {r.severidad}
            </span>
            <button
              onClick={() => toggleRegla(r.codigo)}
              className={`text-[12px] shrink-0 w-16 text-right ${
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
