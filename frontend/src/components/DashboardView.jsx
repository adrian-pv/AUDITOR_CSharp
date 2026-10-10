import CriteriaPanel from "./CriteriaPanel";

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

export default function DashboardView({ report, onOpenFile, onReporteActualizado }) {
  const { stats, hallazgos, cumplimiento_por_modulo } = report;

  const statCards = [
    { label: "Líneas analizadas", value: stats.loc_total.toLocaleString("es-GT") },
    { label: "Vulnerabilidades abiertas", value: stats.vulnerabilidades, tone: "text-red-700" },
    { label: "Densidad de errores", value: `${stats.densidad_errores} / 100 LOC` },
    { label: "Score de gobierno", value: `${stats.score_gobierno}%`, tone: "text-emerald-700" },
  ];

  return (
    <div className="p-8 max-w-5xl space-y-8">
      <div className="grid grid-cols-4 gap-px bg-stone-200 border border-stone-200 rounded-lg overflow-hidden">
        {statCards.map((s) => (
          <div key={s.label} className="bg-white p-4">
            <p className="text-[11px] text-stone-500">{s.label}</p>
            <p className={`text-xl font-semibold mt-1 ${s.tone || "text-stone-900"}`}>{s.value}</p>
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
          {hallazgos.map((h) => (
            <button
              key={h.hallazgo_id ?? `${h.id}-${h.linea}`}
              onClick={() => onOpenFile(h.archivo)}
              className="w-full flex items-center gap-4 px-4 py-3 text-left hover:bg-stone-50"
            >
              <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${SEVERITY_DOT[h.severidad]}`} />
              <span className="font-mono text-[12px] text-stone-500 w-16 shrink-0">{h.id}</span>
              <span className="text-[13px] text-stone-800 flex-1 truncate">{h.descripcion}</span>
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
                <span className="font-mono text-stone-800">{valor}%</span>
              </div>
              <div className="h-1 rounded-full bg-stone-100 overflow-hidden">
                <div
                  className="h-full rounded-full bg-stone-900"
                  style={{ width: `${valor}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
