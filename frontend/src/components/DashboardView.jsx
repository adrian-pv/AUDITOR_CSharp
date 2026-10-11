import { useEffect, useState } from "react";
import CriteriaPanel from "./CriteriaPanel";
import useContador from "../ui/useContador";

const SEVERITY_DOT = {
  CRÍTICO: "bg-red-500",
  ADVERTENCIA: "bg-amber-500",
  BAJO: "bg-stone-400",
};

const SEVERITY_TEXT = {
  CRÍTICO: "text-red-700",
  ADVERTENCIA: "text-amber-700",
  BAJO: "text-stone-500",
};

function Cifra({ valor, decimales = 0, sufijo = "", tono }) {
  const v = useContador(valor);
  const texto = v.toLocaleString("es-GT", { minimumFractionDigits: decimales, maximumFractionDigits: decimales });
  return <p className={`text-xl font-semibold mt-1 tabular-nums ${tono || "text-stone-900"}`}>{texto}{sufijo}</p>;
}

function colorCumplimiento(v) {
  if (v >= 80) return "bg-emerald-600";
  if (v >= 50) return "bg-amber-500";
  return "bg-red-500";
}

function colorScore(v) {
  if (v >= 80) return "text-emerald-700";
  if (v >= 50) return "text-amber-600";
  return "text-red-700";
}

export default function DashboardView({ report, onOpenFile, onReporteActualizado }) {
  const { stats, hallazgos, cumplimiento_por_modulo } = report;
  // Las barras arrancan en 0 y crecen hasta su valor después del primer pintado.
  const [montado, setMontado] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setMontado(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const statCards = [
    { label: "Líneas analizadas", valor: stats.loc_total },
    { label: "Vulnerabilidades abiertas", valor: stats.vulnerabilidades, tono: "text-red-700" },
    { label: "Densidad de errores", valor: stats.densidad_errores, decimales: 2, sufijo: " / 100 LOC" },
    { label: "Score de gobierno", valor: stats.score_gobierno, sufijo: "%", tono: colorScore(stats.score_gobierno) },
  ];

  return (
    <div className="p-8 max-w-5xl space-y-8">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-stone-200 border border-stone-200 rounded-lg overflow-hidden">
        {statCards.map((s, i) => (
          <div key={s.label} className="bg-white p-4 animate-fade-up" style={{ animationDelay: `${i * 50}ms` }}>
            <p className="text-[11px] text-stone-500">{s.label}</p>
            <Cifra valor={s.valor} decimales={s.decimales} sufijo={s.sufijo} tono={s.tono} />
          </div>
        ))}
      </div>

      <CriteriaPanel report={report} onActualizado={onReporteActualizado} />

      <section>
        <h2 className="text-[13px] font-medium text-stone-900 mb-3">
          Hallazgos recientes
        </h2>
        <div className="border border-stone-200 rounded-lg divide-y divide-stone-200 bg-white">
          {hallazgos.length === 0 && (
            <p className="px-4 py-3 text-[12.5px] text-stone-500">Sin hallazgos para los criterios seleccionados.</p>
          )}
          {hallazgos.map((h, i) => (
            <button
              key={h.hallazgo_id ?? `${h.id}-${h.linea}`}
              onClick={() => onOpenFile(h.archivo)}
              style={{ animationDelay: `${Math.min(i, 12) * 25}ms` }}
              className="animate-fade-up group w-full flex items-center gap-4 px-4 py-3 text-left hover:bg-stone-50 transition-colors"
            >
              <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${SEVERITY_DOT[h.severidad]}`} />
              <span className="font-mono text-[12px] text-stone-500 w-16 shrink-0">{h.id}</span>
              <span className="text-[13px] text-stone-800 flex-1 truncate group-hover:text-stone-950">{h.descripcion}</span>
              <span className="font-mono text-[11px] text-stone-400 shrink-0">
                {h.archivo}:{h.linea}
              </span>
              <span className={`text-[11px] shrink-0 ${SEVERITY_TEXT[h.severidad]}`}>
                {h.severidad}
              </span>
            </button>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-[13px] font-medium text-stone-900 mb-3">
          Cumplimiento por módulo
        </h2>
        <div className="border border-stone-200 rounded-lg bg-white p-5 space-y-4">
          {Object.entries(cumplimiento_por_modulo).map(([modulo, valor]) => (
            <div key={modulo}>
              <div className="flex justify-between text-[12px] text-stone-600 mb-1">
                <span>{modulo}</span>
                <span className="font-mono text-stone-800 tabular-nums">{valor}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-stone-100 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-[width,background-color] duration-700 ease-[cubic-bezier(.2,.8,.2,1)] ${colorCumplimiento(valor)}`}
                  style={{ width: montado ? `${valor}%` : "0%" }}
                />
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
