import { useEffect, useState } from "react";
import { History } from "lucide-react";
import { listarReportes } from "../api/reportClient";
import { useAuth } from "../auth/AuthContext";
import { VEREDICTO } from "./VeredictoBanner";

export function formatearFecha(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("es-GT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function HistoryView({ reporteActual, onAbrir }) {
  const { usuario } = useAuth();
  const [reportes, setReportes] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    listarReportes().then(setReportes).catch((e) => setError(e.message));
  }, []);

  const alcance =
    usuario.rol === "Desarrollador"
      ? "Sus análisis, del más reciente al más antiguo."
      : "Análisis de todos los desarrolladores, del más reciente al más antiguo.";

  return (
    <div className="p-8 max-w-5xl space-y-4">
      <p className="text-[13px] text-stone-500">{alcance}</p>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-2.5 text-[12.5px] text-red-700">{error}</div>
      )}

      {!reportes && !error && (
        <div className="border border-stone-200 rounded-lg bg-white divide-y divide-stone-100">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="flex gap-6 px-4 py-3.5">
              <div className="skeleton h-3 w-32" />
              <div className="skeleton h-3 w-28" />
              <div className="skeleton h-3 flex-1" />
              <div className="skeleton h-3 w-10" />
            </div>
          ))}
        </div>
      )}

      {reportes && reportes.length === 0 && (
        <div className="animate-fade-up border border-dashed border-stone-300 rounded-lg bg-white p-10 text-center">
          <History size={20} className="mx-auto text-stone-400" />
          <p className="text-[13px] text-stone-700 mt-3">Todavía no hay reportes.</p>
          <p className="text-[12px] text-stone-500 mt-1">
            {usuario.rol === "Auditor"
              ? "Aparecerán aquí cuando un desarrollador analice un proyecto."
              : "Use “Analizar carpeta…” para generar el primero."}
          </p>
        </div>
      )}

      {reportes && reportes.length > 0 && (
        <div className="border border-stone-200 rounded-lg bg-white overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="text-left text-[11px] text-stone-500 border-b border-stone-200">
                <th className="px-4 py-2.5 font-medium">Proyecto</th>
                <th className="px-4 py-2.5 font-medium">Fecha y hora</th>
                <th className="px-4 py-2.5 font-medium">Generado por</th>
                <th className="px-4 py-2.5 font-medium text-right">Criterios</th>
                <th className="px-4 py-2.5 font-medium text-right">Hallazgos</th>
                <th className="px-4 py-2.5 font-medium text-right">Score</th>
                <th className="px-4 py-2.5 font-medium">Veredicto</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-200">
              {reportes.map((r, i) => {
                const activo = r.reporte_id === reporteActual;
                return (
                  <tr
                    key={r.reporte_id}
                    onClick={() => onAbrir(r.reporte_id)}
                    style={{ animationDelay: `${Math.min(i, 12) * 25}ms` }}
                    className={`animate-fade-up cursor-pointer transition-colors ${activo ? "bg-emerald-50/60" : "hover:bg-stone-50"}`}
                  >
                    <td className="px-4 py-2.5 font-mono text-[12.5px] text-stone-800">{r.proyecto}</td>
                    <td className="px-4 py-2.5 text-stone-600">{formatearFecha(r.generado_en)}</td>
                    <td className="px-4 py-2.5 text-stone-600">{r.generado_por}</td>
                    <td className="px-4 py-2.5 text-right font-mono text-stone-600">
                      {r.criterios_total ? `${r.criterios_evaluados}/${r.criterios_total}` : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-red-700">{r.vulnerabilidades}</td>
                    <td className="px-4 py-2.5 text-right font-mono text-stone-800">{r.score_gobierno}%</td>
                    <td className="px-4 py-2.5">
                      {VEREDICTO[r.veredicto] && (
                        <span className={`whitespace-nowrap text-[11px] px-1.5 py-0.5 rounded border ${VEREDICTO[r.veredicto].insignia}`}>
                          {VEREDICTO[r.veredicto].titulo}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
