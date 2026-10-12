import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";

/** Calcula el veredicto en el navegador para reportes que no lo traen (p. ej. el de muestra). */
export function veredictoDe(report) {
  if (report.veredicto) return report.veredicto;
  const c = { CRÍTICO: 0, ADVERTENCIA: 0, BAJO: 0 };
  for (const h of report.hallazgos || []) c[h.severidad] = (c[h.severidad] || 0) + 1;
  return {
    estado: c.CRÍTICO ? "NO_APROBADO" : c.ADVERTENCIA || c.BAJO ? "APROBADO_CON_ADVERTENCIAS" : "APROBADO",
    criticos: c.CRÍTICO,
    advertencias: c.ADVERTENCIA,
    bajos: c.BAJO,
    reglas_criticas: [...new Set((report.hallazgos || []).filter((h) => h.severidad === "CRÍTICO").map((h) => h.id))].sort(),
  };
}

export const VEREDICTO = {
  APROBADO: { titulo: "Aprobado", caja: "border-emerald-200 bg-emerald-50", texto: "text-emerald-800", icono: CheckCircle2, insignia: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  APROBADO_CON_ADVERTENCIAS: { titulo: "Aprobado con advertencias", caja: "border-amber-200 bg-amber-50", texto: "text-amber-800", icono: AlertTriangle, insignia: "bg-amber-50 text-amber-700 border-amber-200" },
  NO_APROBADO: { titulo: "No aprobado", caja: "border-red-200 bg-red-50", texto: "text-red-800", icono: XCircle, insignia: "bg-red-50 text-red-700 border-red-200" },
};

const plural = (n, s, p) => `${n} ${n === 1 ? s : p}`;

/** Veredicto del reporte para su paso a producción, según los criterios evaluados. */
export default function VeredictoBanner({ report }) {
  const v = veredictoDe(report);
  const e = VEREDICTO[v.estado];
  const Icono = e.icono;

  let detalle;
  if (v.estado === "APROBADO") {
    detalle = "No se encontraron hallazgos en los criterios evaluados. El código puede pasar a producción.";
  } else if (v.estado === "APROBADO_CON_ADVERTENCIAS") {
    const partes = [v.advertencias && plural(v.advertencias, "advertencia", "advertencias"), v.bajos && plural(v.bajos, "hallazgo de severidad baja", "hallazgos de severidad baja")].filter(Boolean);
    detalle = `Sin hallazgos críticos. Hay ${partes.join(" y ")}: conviene ${v.bajos ? "revisarlos" : "revisarlas"}, pero no impiden el paso a producción.`;
  } else {
    detalle = `${plural(v.criticos, "hallazgo crítico", "hallazgos críticos")} impiden el paso a producción. Corríjalos y vuelva a analizar el proyecto.`;
    if (v.advertencias) detalle += ` También hay ${plural(v.advertencias, "advertencia", "advertencias")}.`;
  }

  return (
    <div key={v.estado} role="status" className={`animate-fade-up flex items-start gap-3 rounded-lg border px-4 py-3 ${e.caja}`}>
      <Icono size={18} className={`mt-0.5 shrink-0 ${e.texto}`} />
      <div className="min-w-0">
        <p className={`text-[13px] font-medium ${e.texto}`}>{e.titulo} para producción</p>
        <p className={`text-[12.5px] mt-0.5 ${e.texto} opacity-90`}>{detalle}</p>
        {v.estado === "NO_APROBADO" && v.reglas_criticas.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {v.reglas_criticas.map((c) => (
              <span key={c} className="font-mono text-[11px] px-1.5 py-0.5 rounded border border-red-200 bg-white text-red-700">{c}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
