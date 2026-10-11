import { useEffect, useRef, useState } from "react";
import { Download, FileUp, FolderSearch, Loader2 } from "lucide-react";
import {
  analyzeFolder,
  descargarJson,
  exportarReporte,
  fetchSampleReport,
  listarReportes,
  nombreArchivoReporte,
  obtenerReporte,
  vistaDeArchivo,
} from "./api/reportClient";
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
import { useToast } from "./ui/Toast";

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
  const toast = useToast();
  const [view, setView] = useState("dashboard");
  const [report, setReport] = useState(null);
  const [openFile, setOpenFile] = useState(null);
  const [analizando, setAnalizando] = useState(false);
  const [error, setError] = useState(null);
  const [dialogoAbierto, setDialogoAbierto] = useState(false);
  const reglasElegidas = useRef(null);
  const folderInputRef = useRef(null);
  const jsonInputRef = useRef(null);
  const [descargando, setDescargando] = useState(false);

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
      // En un reporte cargado, hallazgo_id es la posición dentro del archivo.
      ...(r.importado && {
        documento: {
          ...r.documento,
          hallazgos: r.documento.hallazgos.map((h, i) => (i === hallazgoId ? { ...h, estado } : h)),
        },
      }),
    }));

  // Descargar el reporte abierto como .json (el cargado se descarga con los cambios del auditor).
  const descargar = async () => {
    setError(null);
    setDescargando(true);
    try {
      const documento = report.importado ? report.documento : await exportarReporte(report.reporte_id);
      descargarJson(documento, nombreArchivoReporte(documento.proyecto, documento.generado_en));
      toast("Reporte descargado como .json.");
    } catch (err) {
      setError(err.message);
    } finally {
      setDescargando(false);
    }
  };

  // Cargar un .json (p. ej. de un tercero): se muestra sin analizar ni guardar nada.
  const onJsonSeleccionado = async (e) => {
    const archivo = e.target.files?.[0];
    e.target.value = "";
    if (!archivo) return;
    setError(null);
    if (archivo.size > 20 * 1024 * 1024) {
      setError("El archivo es demasiado grande (máximo 20 MB).");
      return;
    }
    let documento;
    try {
      documento = JSON.parse(await archivo.text());
    } catch {
      setError(`'${archivo.name}' no es un archivo JSON válido.`);
      return;
    }
    try {
      const vista = await vistaDeArchivo(documento);
      setReport(vista);
      setOpenFile(null);
      setView("dashboard");
      toast(`Reporte de ${vista.proyecto} cargado. No se guarda en el historial.`);
    } catch (err) {
      setError(`No se pudo cargar '${archivo.name}': ${err.message}`);
    }
  };

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
      const nuevo = await analyzeFolder(files, reglasElegidas.current);
      setReport(nuevo);
      setOpenFile(null);
      setView("dashboard");
      toast(`Análisis de ${nuevo.proyecto} completado: ${nuevo.stats.vulnerabilidades} hallazgo(s).`);
    } catch (err) {
      setError(err.message);
    } finally {
      setAnalizando(false);
    }
  };

  const esReal = Boolean(report?.reporte_id) && !report?.importado;
  const descargable = esReal || Boolean(report?.importado);

  return (
    <div className="h-screen flex bg-stone-50">
      <Sidebar active={view} onNavigate={setView} />
      <main className="flex-1 overflow-y-auto">
        <header className="relative h-14 border-b border-stone-200 flex items-center justify-between px-8 gap-4 bg-stone-50/90 backdrop-blur sticky top-0 z-20">
          {/* barra de progreso mientras corre el análisis */}
          {analizando && (
            <div className="absolute left-0 right-0 -bottom-px h-0.5 overflow-hidden bg-emerald-100">
              <div className="h-full w-2/5 bg-emerald-600 animate-progreso" />
            </div>
          )}
          <div className="flex items-center gap-3 min-w-0">
            <h1 className="text-[13px] text-stone-900 font-medium shrink-0">{TITULOS[view]}</h1>
            {report && VISTAS_DE_REPORTE.has(view) && (
              <span
                key={report.reporte_id || "muestra"}
                title={report.importado ? "Cargado desde un archivo .json: no está en el historial" : undefined}
                className={`animate-fade-in text-[10.5px] px-1.5 py-0.5 rounded truncate ${
                  report.importado
                    ? "bg-sky-50 text-sky-700 border border-sky-200"
                    : esReal
                    ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                    : "bg-stone-100 text-stone-500 border border-stone-200"
                }`}
              >
                {report.importado
                  ? `Archivo .json · ${report.proyecto}${report.generado_en ? ` · ${formatearFecha(report.generado_en)}` : ""} · sin guardar`
                  : esReal
                  ? `${report.proyecto} · ${formatearFecha(report.generado_en)} · ${report.generado_por}`
                  : "Reporte de muestra"}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
          {report && descargable && VISTAS_DE_REPORTE.has(view) && (
            <button
              onClick={descargar}
              disabled={descargando}
              title="Descargar este reporte como archivo .json"
              className="btn-press animate-fade-in flex items-center gap-2 text-[12.5px] px-3 py-1.5 rounded-md text-stone-600 hover:bg-stone-100 transition-colors disabled:opacity-60"
            >
              {descargando ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
              Descargar .json
            </button>
          )}
          <button
            onClick={() => jsonInputRef.current?.click()}
            title="Ver un reporte .json (propio o de un tercero) sin guardarlo"
            className="btn-press flex items-center gap-2 text-[12.5px] px-3 py-1.5 rounded-md border border-stone-300 bg-white text-stone-700 hover:bg-stone-100 hover:border-stone-400 transition-colors"
          >
            <FileUp size={14} /> Cargar .json
          </button>
          {puedeAnalizar && (
            <button
              onClick={elegirCarpeta}
              disabled={analizando}
              className="btn-press shrink-0 flex items-center gap-2 text-[12.5px] px-3 py-1.5 rounded-md border border-stone-300 bg-white text-stone-700 hover:bg-stone-100 hover:border-stone-400 transition-colors disabled:opacity-60"
            >
              {analizando ? <Loader2 size={14} className="animate-spin" /> : <FolderSearch size={14} />}
              {analizando ? "Analizando…" : "Analizar carpeta…"}
            </button>
          )}
          </div>
          <input ref={jsonInputRef} type="file" accept=".json,application/json" className="hidden" onChange={onJsonSeleccionado} />

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
          <div className="animate-fade-up mx-8 mt-4 rounded-md border border-red-200 bg-red-50 px-4 py-2.5 text-[12.5px] text-red-700">
            {error}
          </div>
        )}

        {!report && VISTAS_DE_REPORTE.has(view) && <EsqueletoReporte />}
        <div key={view} className="animate-fade-up">
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
        {view === "history" && <HistoryView reporteActual={report?.importado ? null : report?.reporte_id} onAbrir={abrirReporte} />}
        {view === "rules" && <RulesView />}
        {view === "users" && <UsersView />}
        {view === "profile" && <ProfileView />}
        </div>

        {dialogoAbierto && (
          <AnalyzeDialog onCancelar={() => setDialogoAbierto(false)} onContinuar={onReglasElegidas} />
        )}
      </main>
    </div>
  );
}

function EsqueletoReporte() {
  return (
    <div className="p-8 max-w-5xl space-y-8" aria-label="Cargando reporte">
      <div className="grid grid-cols-4 gap-3">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="bg-white border border-stone-200 rounded-lg p-4 space-y-2">
            <div className="skeleton h-3 w-24" />
            <div className="skeleton h-6 w-16" />
          </div>
        ))}
      </div>
      <div className="bg-white border border-stone-200 rounded-lg divide-y divide-stone-100">
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} className="flex gap-4 px-4 py-3.5">
            <div className="skeleton h-3 w-14" />
            <div className="skeleton h-3 flex-1" />
            <div className="skeleton h-3 w-28" />
          </div>
        ))}
      </div>
    </div>
  );
}
