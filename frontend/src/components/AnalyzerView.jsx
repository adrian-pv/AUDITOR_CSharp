import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, FileCode2 } from "lucide-react";

const SEVERITY_TEXT = {
  CRÍTICO: "text-red-700 bg-red-50 border-red-200",
  ADVERTENCIA: "text-amber-700 bg-amber-50 border-amber-200",
  BAJO: "text-stone-600 bg-stone-100 border-stone-200",
};

export default function AnalyzerView({ report, openFile, onSelectFile }) {
  const archivosConHallazgos = useMemo(() => {
    const porArchivo = new Map();
    for (const h of report.hallazgos) {
      if (!porArchivo.has(h.archivo)) porArchivo.set(h.archivo, []);
      porArchivo.get(h.archivo).push(h);
    }
    return porArchivo;
  }, [report]);

  const [expandido, setExpandido] = useState(openFile || [...archivosConHallazgos.keys()][0]);

  const toggle = (archivo) => {
    const next = expandido === archivo ? null : archivo;
    setExpandido(next);
    onSelectFile?.(next);
  };

  return (
    <div className="p-8 max-w-5xl">
      <p className="text-[13px] text-stone-500 mb-4">
        {archivosConHallazgos.size} archivo(s) con hallazgos activos, de la solución
        <span className="font-mono text-stone-700"> AtuneraPacifico</span>
      </p>

      <div className="border border-stone-200 rounded-lg divide-y divide-stone-200 bg-white">
        {[...archivosConHallazgos.entries()].map(([archivo, hallazgos]) => {
          const isOpen = expandido === archivo;
          return (
            <div key={archivo}>
              <button
                onClick={() => toggle(archivo)}
                className="w-full flex items-center gap-2.5 px-4 py-3 text-left hover:bg-stone-50"
              >
                {isOpen ? (
                  <ChevronDown size={14} className="text-stone-400 shrink-0" />
                ) : (
                  <ChevronRight size={14} className="text-stone-400 shrink-0" />
                )}
                <FileCode2 size={14} className="text-stone-400 shrink-0" />
                <span className="font-mono text-[12.5px] text-stone-800 flex-1">{archivo}</span>
                <span className="text-[11px] text-stone-500">
                  {hallazgos.length} hallazgo{hallazgos.length > 1 ? "s" : ""}
                </span>
              </button>

              {isOpen && (
                <div className="px-4 pb-4 pl-10 space-y-3">
                  {hallazgos.map((h) => (
                    <div
                      key={`${h.id}-${h.linea}`}
                      className={`rounded-md border px-3 py-2.5 ${SEVERITY_TEXT[h.severidad]}`}
                    >
                      <div className="flex items-center gap-2 text-[12px] font-medium">
                        <span className="font-mono">{h.id}</span>
                        <span>·</span>
                        <span>línea {h.linea}</span>
                        <span className="ml-auto text-[10.5px] uppercase tracking-wide">
                          {h.severidad}
                        </span>
                      </div>
                      <p className="text-[12.5px] mt-1.5 text-stone-700">{h.descripcion}</p>
                      <p className="text-[12px] mt-1 text-stone-500">
                        <span className="font-medium">Recomendación: </span>
                        {h.recomendacion}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
