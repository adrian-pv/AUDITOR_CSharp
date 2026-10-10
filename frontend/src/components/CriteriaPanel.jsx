import { useState } from "react";
import { Loader2 } from "lucide-react";
import { guardarCriterios } from "../api/reportClient";
import { useAuth } from "../auth/AuthContext";

const SEVERITY_TEXT = {
  CRÍTICO: "text-red-700",
  ADVERTENCIA: "text-amber-700",
  BAJO: "text-stone-500",
};

/**
 * Criterios de evaluación de un reporte: las reglas que se aplicaron en el
 * análisis. El Auditor (o el Administrador) marca cuáles evaluar; la selección
 * se guarda en la base de datos y el panel se recalcula solo con esas reglas.
 */
export default function CriteriaPanel({ report, onActualizado }) {
  const { puedeEvaluar } = useAuth();
  const [guardando, setGuardando] = useState(null);
  const [error, setError] = useState(null);
  const criterios = report.criterios || [];
  if (!report.reporte_id || criterios.length === 0) return null;

  const evaluadas = criterios.filter((c) => c.evaluada).map((c) => c.codigo);

  const toggle = async (codigo) => {
    const nuevas = evaluadas.includes(codigo) ? evaluadas.filter((c) => c !== codigo) : [...evaluadas, codigo];
    if (nuevas.length === 0) {
      setError("Debe quedar al menos un criterio seleccionado.");
      return;
    }
    setError(null);
    setGuardando(codigo);
    try {
      onActualizado(await guardarCriterios(report.reporte_id, nuevas));
    } catch (err) {
      setError(err.message);
    } finally {
      setGuardando(null);
    }
  };

  return (
    <section>
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="text-[13px] font-medium text-stone-900">Criterios de evaluación</h2>
        <span className="text-[11px] text-stone-500">
          {evaluadas.length} de {criterios.length} reglas evaluadas ·{" "}
          {puedeEvaluar ? "marque las reglas que desea evaluar" : "los elige el auditor"}
        </span>
      </div>
      {error && <p className="text-[12px] text-red-700 mb-2">{error}</p>}
      <div className="border border-stone-200 rounded-lg bg-white p-3 flex flex-wrap gap-2">
        {criterios.map((c) => (
          <label
            key={c.codigo}
            title={c.nombre}
            className={`flex items-center gap-2 rounded-md border px-3 py-1.5 text-[12px] ${
              c.evaluada ? "border-stone-300 bg-white text-stone-800" : "border-dashed border-stone-300 bg-stone-50 text-stone-400"
            } ${puedeEvaluar ? "cursor-pointer hover:border-stone-500" : ""}`}
          >
            {guardando === c.codigo ? (
              <Loader2 size={13} className="animate-spin text-stone-400" />
            ) : (
              <input
                type="checkbox"
                checked={c.evaluada}
                disabled={!puedeEvaluar || guardando !== null}
                onChange={() => toggle(c.codigo)}
                className="accent-stone-900"
              />
            )}
            <span className="font-mono">{c.codigo}</span>
            <span className="text-stone-500">{c.modulo.replace(/^Módulo \d: /, "")}</span>
            <span className={c.evaluada ? SEVERITY_TEXT[c.severidad] : ""}>
              · {c.hallazgos} hallazgo{c.hallazgos === 1 ? "" : "s"}
            </span>
          </label>
        ))}
      </div>
    </section>
  );
}
