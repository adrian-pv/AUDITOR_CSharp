import { useEffect, useRef, useState } from "react";
import { FolderSearch, Loader2 } from "lucide-react";
import { fetchSampleReport, analyzeFolder } from "./api/reportClient";
import Sidebar from "./components/Sidebar";
import DashboardView from "./components/DashboardView";
import AnalyzerView from "./components/AnalyzerView";
import RulesView from "./components/RulesView";

function formatearFecha(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("es-GT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function App() {
  const [view, setView] = useState("dashboard");
  const [report, setReport] = useState(null);
  const [openFile, setOpenFile] = useState(null);
  const [esReporteReal, setEsReporteReal] = useState(false);
  const [analizando, setAnalizando] = useState(false);
  const [error, setError] = useState(null);
  const folderInputRef = useRef(null);

  useEffect(() => {
    fetchSampleReport().then(setReport);
  }, []);

  const goToFile = (archivo) => {
    setOpenFile(archivo);
    setView("analyzer");
  };

  const elegirCarpeta = () => {
    setError(null);
    folderInputRef.current?.click();
  };

  const onCarpetaSeleccionada = async (e) => {
    const files = Array.from(e.target.files || []);
    e.target.value = ""; // permite volver a elegir la misma carpeta después
    if (files.length === 0) return;

    setAnalizando(true);
    setError(null);
    try {
      const nuevoReporte = await analyzeFolder(files);
      setReport(nuevoReporte);
      setEsReporteReal(true);
      setOpenFile(null);
      setView("dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setAnalizando(false);
    }
  };

  if (!report) {
    return (
      <div className="h-screen flex items-center justify-center text-stone-400 text-sm">
        Cargando reporte…
      </div>
    );
  }

  return (
    <div className="h-screen flex bg-stone-50">
      <Sidebar active={view} onNavigate={setView} auditor={report.auditor} />
      <main className="flex-1 overflow-y-auto">
        <header className="h-14 border-b border-stone-200 flex items-center justify-between px-8">
          <div className="flex items-center gap-3">
            <h1 className="text-[13px] text-stone-500">
              Sistema de Gobierno de Código Automático
            </h1>
            <span
              className={`text-[10px] px-1.5 py-0.5 rounded ${
                esReporteReal
                  ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                  : "bg-stone-100 text-stone-500 border border-stone-200"
              }`}
            >
              {esReporteReal
                ? `Análisis real — ${report.proyecto} · ${formatearFecha(report.generado_en)}`
                : "Reporte de muestra"}
            </span>
          </div>

          <button
            onClick={elegirCarpeta}
            disabled={analizando}
            className="flex items-center gap-2 text-[12.5px] px-3 py-1.5 rounded-md border border-stone-300 text-stone-700 hover:bg-stone-100 disabled:opacity-50"
          >
            {analizando ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <FolderSearch size={14} />
            )}
            {analizando ? "Analizando…" : "Analizar carpeta…"}
          </button>

          {/* input oculto: 'webkitdirectory' permite elegir una carpeta completa */}
          <input
            ref={folderInputRef}
            type="file"
            webkitdirectory=""
            directory=""
            multiple
            className="hidden"
            onChange={onCarpetaSeleccionada}
          />
        </header>

        {error && (
          <div className="mx-8 mt-4 rounded-md border border-red-200 bg-red-50 px-4 py-2.5 text-[12.5px] text-red-700">
            {error}
          </div>
        )}

        {view === "dashboard" && <DashboardView report={report} onOpenFile={goToFile} />}
        {view === "analyzer" && (
          <AnalyzerView report={report} openFile={openFile} onSelectFile={setOpenFile} />
        )}
        {view === "rules" && <RulesView />}
      </main>
    </div>
  );
}
