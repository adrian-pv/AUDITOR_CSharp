import { useMemo, useState } from "react";
import { ChevronRight, FileCode2 } from "lucide-react";
import { useToast } from "../ui/Toast";
import { evaluarHallazgo } from "../api/reportClient";
import { useAuth } from "../auth/AuthContext";

const ESTADOS = ["Pendiente", "Solucionado", "Fallido"];
const ESTADO_COLOR = {
  Pendiente: "bg-white border-stone-300 text-stone-700",
  Solucionado: "bg-emerald-50 border-emerald-300 text-emerald-800",
  Fallido: "bg-red-50 border-red-300 text-red-800",
};

const SEVERITY_TEXT = {
  CRÍTICO: "text-red-700 bg-red-50 border-red-200",
  ADVERTENCIA: "text-amber-700 bg-amber-50 border-amber-200",
  BAJO: "text-stone-600 bg-stone-100 border-stone-200",
};

export default function AnalyzerView({ report, openFile, onSelectFile, onHallazgoEvaluado }) {
  const { puedeEvaluar } = useAuth();
  const toast = useToast();
  const [errorEval, setErrorEval] = useState(null);
  // Se evalúan los reportes guardados en la BD y los cargados desde .json (el de muestra no).
  const evaluable = puedeEvaluar && (report.reporte_id || report.importado);

  const cambiarEstado = async (h, estado) => {
    setErrorEval(null);
    try {
      // Un reporte cargado desde .json no está en la BD: el cambio queda en pantalla
      // y viaja en el archivo cuando se vuelve a descargar.
      if (!report.importado) await evaluarHallazgo(h.hallazgo_id, estado);
      onHallazgoEvaluado?.(h.hallazgo_id, estado);
      toast(`${h.id} (línea ${h.linea}) marcado como ${estado}.`);
    } catch (err) {
      setErrorEval(err.message);
    }
  };

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
        <span className="font-mono text-stone-700"> {report.proyecto || "AtuneraPacifico"}</span>
      </p>

      {errorEval && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-2.5 text-[12.5px] text-red-700">
          {errorEval}
        </div>
      )}

      <div className="border border-stone-200 rounded-lg divide-y divide-stone-200 bg-white">
        {[...archivosConHallazgos.entries()].map(([archivo, hallazgos]) => {
          const isOpen = expandido === archivo;
          return (
            <div key={archivo}>
              <button
                onClick={() => toggle(archivo)}
                aria-expanded={isOpen}
                className="w-full flex items-center gap-2.5 px-4 py-3 text-left hover:bg-stone-50 transition-colors"
              >
                <ChevronRight
                  size={14}
                  className={`text-stone-400 shrink-0 transition-transform duration-200 ${isOpen ? "rotate-90" : ""}`}
                />
                <FileCode2 size={14} className="text-stone-400 shrink-0" />
                <span className="font-mono text-[12.5px] text-stone-800 flex-1">{archivo}</span>
                <span className="text-[11px] text-stone-500">
                  {hallazgos.length} hallazgo{hallazgos.length > 1 ? "s" : ""}
                </span>
              </button>

              {/* expansión suave: la fila pasa de 0fr a 1fr de alto */}
              <div
                className={`grid transition-[grid-template-rows,opacity] duration-300 ease-[cubic-bezier(.2,.8,.2,1)] ${
                  isOpen ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
                }`}
                aria-hidden={!isOpen}
              >
                <div className="overflow-hidden">
                <div className="px-4 pb-4 pl-10 space-y-3">
                  {hallazgos.map((h) => (
                    <div
                      key={h.hallazgo_id ?? `${h.id}-${h.linea}`}
                      className={`rounded-md border px-3 py-2.5 ${SEVERITY_TEXT[h.severidad]}`}
                    >
                      <div className="flex items-center gap-2 text-[12px] font-medium">
                        <span className="font-mono">{h.id}</span>
                        <span>·</span>
                        <span>línea {h.linea}</span>
                        {[h.owasp_2021, h.owasp_2025, h.cwe].filter(Boolean).map((t) => (
                          <span key={t} className="font-mono text-[10.5px] font-normal px-1.5 py-px rounded border border-current/20 bg-white/60">
                            {t}
                          </span>
                        ))}
                        <span className="ml-auto text-[10.5px] uppercase tracking-wide">
                          {h.severidad}
                        </span>
                      </div>
                      <p className="text-[12.5px] mt-1.5 text-stone-700">{h.descripcion}</p>
                      <p className="text-[12px] mt-1 text-stone-500">
                        <span className="font-medium">Recomendación: </span>
                        {h.recomendacion}
                      </p>
                      <div className="mt-2 flex items-center gap-2 text-[11.5px] text-stone-500">
                        Estado:
                        {evaluable ? (
                          <select
                            key={h.estado}
                            value={h.estado}
                            onChange={(e) => cambiarEstado(h, e.target.value)}
                            tabIndex={isOpen ? 0 : -1}
                            className={`animate-pop h-7 rounded border px-1.5 text-[11.5px] transition-colors ${ESTADO_COLOR[h.estado]}`}
                          >
                            {ESTADOS.map((e) => (
                              <option key={e}>{e}</option>
                            ))}
                          </select>
                        ) : (
                          <span className={`rounded border px-1.5 py-0.5 ${ESTADO_COLOR[h.estado]}`}>{h.estado}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
