import { useState } from "react";
import { guardarCriterios } from "../api/reportClient";
import { useAuth } from "../auth/AuthContext";
import Switch from "../ui/Switch";
import { useToast } from "../ui/Toast";

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
  const toast = useToast();
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
      toast(`Criterio ${codigo} ${nuevas.includes(codigo) ? "incluido en" : "excluido de"} la evaluación.`);
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
      {error && <p key={error} className="animate-shake text-[12px] text-red-700 mb-2">{error}</p>}
      <div className="border border-stone-200 rounded-lg bg-white p-3 flex flex-wrap gap-2">
        {criterios.map((c) => (
          <div
            key={c.codigo}
            title={c.nombre}
            className={`flex items-center gap-2 rounded-md border px-3 py-1.5 text-[12px] transition-all duration-200 ${
              c.evaluada ? "border-stone-300 bg-white text-stone-800" : "border-dashed border-stone-300 bg-stone-50 text-stone-400"
            } ${puedeEvaluar ? "cursor-pointer hover:border-stone-500" : ""}`}
          >
            <Switch
              checked={c.evaluada}
              onChange={() => toggle(c.codigo)}
              disabled={!puedeEvaluar || (guardando !== null && guardando !== c.codigo)}
              cargando={guardando === c.codigo}
              tamano="sm"
              etiqueta={`${c.evaluada ? "Excluir" : "Incluir"} ${c.codigo}`}
            />
            <span className="font-mono">{c.codigo}</span>
            <span className="text-stone-500">{c.modulo.replace(/^Módulo \d: /, "")}</span>
            <span className={c.evaluada ? SEVERITY_TEXT[c.severidad] : ""}>
              · {c.hallazgos} hallazgo{c.hallazgos === 1 ? "" : "s"}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
