import { useEffect, useRef, useState } from "react";
import { FolderSearch, Loader2 } from "lucide-react";
import { analyzeFolder, fetchSampleReport, listarReportes, obtenerReporte } from "./api/reportClient";
import { useAuth } from "./auth/AuthContext";
import Sidebar from "./components/Sidebar";
import LoginView from "./components/LoginView";
import DashboardView from "./components/DashboardView";
import AnalyzerView from "./components/AnalyzerView";
import RulesView from "./components/RulesView";
import HistoryView, { formatearFecha } from "./components/HistoryView";
import ProfileView from "./components/ProfileView";
import UsersView from "./components/UsersView";
import AnalyzeDialog from "./components/AnalyzeDialog";

const TITULOS = {
  dashboard: "Panel General",
  analyzer: "Analizador",
  history: "Historial de reportes",
  rules: "Reglas y Políticas",
  users: "Usuarios",
  profile: "Mi perfil",
};

// Vistas que muestran el reporte abierto (las demás no necesitan la etiqueta del reporte).
const VISTAS_DE_REPORTE = new Set(["dashboard", "analyzer"]);

export default function App() {
  const { usuario, cargando } = useAuth();

  if (cargando) {
    return (
      <div className="h-screen flex items-center justify-center text-stone-400 text-sm">Cargando…</div>
    );
  }
  if (!usuario) return <LoginView />;
  // key: al cambiar de usuario se reinicia todo el estado de la aplicación.
  return <Workspace key={usuario.id} />;
}

function Workspace() {
  const { puedeAnalizar } = useAuth();
  const [view, setView] = useState("dashboard");
  const [report, setReport] = useState(null);
  const [openFile, setOpenFile] = useState(null);
  const [analizando, setAnalizando] = useState(false);
  const [error, setError] = useState(null);
  const [dialogoAbierto, setDialogoAbierto] = useState(false);
  const reglasElegidas = useRef(null);
  const folderInputRef = useRef(null);

  // Al entrar: el reporte más reciente del historial; si no hay, el de muestra.
  useEffect(() => {
    (async () => {
      try {
        const historial = await listarReportes();
        if (historial.length > 0) {
          setReport(await obtenerReporte(historial[0].reporte_id));
          return;
        }
      } catch (err) {
        setError(err.message);
      }
      setReport(await fetchSampleReport());
    })();
  }, []);

  const goToFile = (archivo) => {
    setOpenFile(archivo);
    setView("analyzer");
  };

  const abrirReporte = async (reporteId) => {
    setError(null);
    try {
      setReport(await obtenerReporte(reporteId));
      setOpenFile(null);
      setView("dashboard");
    } catch (err) {
      setError(err.message);
    }
  };

  const onHallazgoEvaluado = (hallazgoId, estado) =>
    setReport((r) => ({
      ...r,
      hallazgos: r.hallazgos.map((h) => (h.hallazgo_id === hallazgoId ? { ...h, estado } : h)),
    }));

  // 1) diálogo de reglas (todas marcadas)  2) selector de carpeta  3) análisis
  const elegirCarpeta = () => {
    setError(null);
    setDialogoAbierto(true);
  };

  const onReglasElegidas = (reglas) => {
    reglasElegidas.current = reglas;
    setDialogoAbierto(false);
    folderInputRef.current?.click();
  };

  const onCarpetaSeleccionada = async (e) => {
    const files = Array.from(e.target.files || []);
    e.target.value = ""; // permite volver a elegir la misma carpeta después
    if (files.length === 0) return;

    setAnalizando(true);
    setError(null);
    try {
      setReport(await analyzeFolder(files, reglasElegidas.current));
      setOpenFile(null);
      setView("dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setAnalizando(false);
    }
  };

  const esReal = Boolean(report?.reporte_id);

  return (
    <div className="h-screen flex bg-stone-50">
      <Sidebar active={view} onNavigate={setView} />
      <main className="flex-1 overflow-y-auto">
        <header className="h-14 border-b border-stone-200 flex items-center justify-between px-8 gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <h1 className="text-[13px] text-stone-900 font-medium shrink-0">{TITULOS[view]}</h1>
            {report && VISTAS_DE_REPORTE.has(view) && (
              <span
                className={`text-[10.5px] px-1.5 py-0.5 rounded truncate ${
                  esReal
                    ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                    : "bg-stone-100 text-stone-500 border border-stone-200"
                }`}
              >
                {esReal
                  ? `${report.proyecto} · ${formatearFecha(report.generado_en)} · ${report.generado_por}`
                  : "Reporte de muestra"}
              </span>
            )}
          </div>

          {puedeAnalizar && (
            <button
              onClick={elegirCarpeta}
              disabled={analizando}
              className="shrink-0 flex items-center gap-2 text-[12.5px] px-3 py-1.5 rounded-md border border-stone-300 text-stone-700 hover:bg-stone-100 disabled:opacity-50"
            >
              {analizando ? <Loader2 size={14} className="animate-spin" /> : <FolderSearch size={14} />}
              {analizando ? "Analizando…" : "Analizar carpeta…"}
            </button>
          )}

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

        {!report && VISTAS_DE_REPORTE.has(view) && (
          <div className="p-8 text-stone-400 text-sm">Cargando reporte…</div>
        )}
        {report && view === "dashboard" && (
          <DashboardView report={report} onOpenFile={goToFile} onReporteActualizado={setReport} />
        )}
        {report && view === "analyzer" && (
          <AnalyzerView
            key={report.reporte_id || "muestra"}
            report={report}
            openFile={openFile}
            onSelectFile={setOpenFile}
            onHallazgoEvaluado={onHallazgoEvaluado}
          />
        )}
        {view === "history" && <HistoryView reporteActual={report?.reporte_id} onAbrir={abrirReporte} />}
        {view === "rules" && <RulesView />}
        {view === "users" && <UsersView />}
        {view === "profile" && <ProfileView />}

        {dialogoAbierto && (
          <AnalyzeDialog onCancelar={() => setDialogoAbierto(false)} onContinuar={onReglasElegidas} />
        )}
      </main>
    </div>
  );
}
