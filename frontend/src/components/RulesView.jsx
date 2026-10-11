import { useEffect, useMemo, useState } from "react";
import { Plus } from "lucide-react";
import { cambiarRegla, listarReglas, plantillasDeReglas } from "../api/adminClient";
import { useAuth } from "../auth/AuthContext";
import RuleEditor from "./RuleEditor";

const SEVERITY_TEXT = {
  CRÍTICO: "text-red-700",
  ADVERTENCIA: "text-amber-700",
  BAJO: "text-stone-500",
};

const FILTROS = [
  ["todos", "Todas"],
  ["Módulo 1: Seguridad", "Seguridad"],
  ["Módulo 2: Rendimiento", "Rendimiento"],
  ["Módulo 3: Memoria", "Memoria"],
  ["Módulo 4: Gobierno", "Gobierno"],
];

function Cobertura({ titulo, categorias, reglas, campo }) {
  return (
    <div>
      <p className="text-[11.5px] text-stone-500 mb-1.5">{titulo}</p>
      <div className="grid grid-cols-5 sm:grid-cols-10 gap-1.5">
        {Object.entries(categorias).map(([codigo, nombre]) => {
          const n = reglas.filter((r) => r.activa && r[campo] === codigo).length;
          return (
            <div
              key={codigo}
              title={`${codigo} ${nombre}: ${n} regla(s) activa(s)`}
              className={`rounded-md border px-1.5 py-1.5 text-center ${n ? "border-stone-300 bg-white" : "border-dashed border-stone-300 bg-stone-50"}`}
            >
              <p className={`font-mono text-[11px] ${n ? "text-stone-800" : "text-stone-400"}`}>{codigo.slice(0, 3)}</p>
              <p className={`text-[15px] font-semibold leading-tight ${n ? "text-emerald-700" : "text-stone-300"}`}>{n}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function RulesView() {
  const { esAdmin } = useAuth();
  const [gatekeeper, setGatekeeper] = useState(true);
  const [reglas, setReglas] = useState([]);
  const [catalogo, setCatalogo] = useState(null);
  const [filtro, setFiltro] = useState("todos");
  const [editando, setEditando] = useState(undefined); // undefined = cerrado, null = nueva
  const [error, setError] = useState(null);
  const [aviso, setAviso] = useState(null);

  useEffect(() => {
    Promise.all([listarReglas(), plantillasDeReglas()])
      .then(([r, c]) => {
        setReglas(r);
        setCatalogo(c);
      })
      .catch((e) => setError(e.message));
  }, []);

  const nombreDetector = useMemo(
    () => Object.fromEntries((catalogo?.detectores || []).map((d) => [d.tipo, d.nombre])),
    [catalogo]
  );
  const visibles = filtro === "todos" ? reglas : reglas.filter((r) => r.modulo === filtro);

  const toggleRegla = async (regla) => {
    setError(null);
    try {
      const actualizada = await cambiarRegla(regla.codigo, !regla.activa);
      setReglas((prev) => prev.map((r) => (r.codigo === actualizada.codigo ? actualizada : r)));
    } catch (err) {
      setError(err.message);
    }
  };

  const onGuardada = (r) => {
    setReglas((prev) => (prev.some((x) => x.codigo === r.codigo) ? prev.map((x) => (x.codigo === r.codigo ? r : x)) : [...prev, r]));
    setAviso(`Regla ${r.codigo} guardada. Se aplicará desde el próximo análisis.`);
    setEditando(undefined);
  };

  return (
    <div className="p-8 max-w-6xl space-y-6">
      <div className="border border-stone-200 rounded-lg bg-white p-4 flex items-center justify-between">
        <div>
          <p className="text-[13px] font-medium text-stone-900">Gatekeeper de gobierno de código</p>
          <p className="text-[12px] text-stone-500 mt-0.5">Bloquea el commit o despliegue si la densidad de errores supera el umbral configurado.</p>
        </div>
        <button
          onClick={() => setGatekeeper((v) => !v)}
          className={`shrink-0 w-10 h-6 rounded-full relative transition-colors ${gatekeeper ? "bg-stone-900" : "bg-stone-300"}`}
        >
          <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-all ${gatekeeper ? "left-[19px]" : "left-0.5"}`} />
        </button>
      </div>

      {catalogo && (
        <div className="border border-stone-200 rounded-lg bg-white p-4 space-y-3">
          <div className="flex items-baseline justify-between">
            <p className="text-[13px] font-medium text-stone-900">Cobertura OWASP Top 10</p>
            <p className="text-[11px] text-stone-500">Reglas activas por categoría</p>
          </div>
          <Cobertura titulo="Edición 2021" categorias={catalogo.owasp_2021} reglas={reglas} campo="owasp_2021" />
          <Cobertura titulo="Edición 2025" categorias={catalogo.owasp_2025} reglas={reglas} campo="owasp_2025" />
        </div>
      )}

      {error && <div className="rounded-md border border-red-200 bg-red-50 px-4 py-2.5 text-[12.5px] text-red-700">{error}</div>}
      {aviso && <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-[12.5px] text-emerald-700">{aviso}</div>}

      <div className="border border-stone-200 rounded-lg bg-white">
        <div className="px-4 py-3 flex flex-wrap items-center gap-3 border-b border-stone-200">
          <span className="text-[13px] font-medium text-stone-900 mr-2">Matriz de reglas (.NET / C#)</span>
          <div className="flex gap-1">
            {FILTROS.map(([valor, etiqueta]) => (
              <button
                key={valor}
                onClick={() => setFiltro(valor)}
                className={`text-[12px] px-2.5 py-1 rounded-md ${filtro === valor ? "bg-stone-900 text-white" : "text-stone-600 hover:bg-stone-100"}`}
              >
                {etiqueta}
              </button>
            ))}
          </div>
          {esAdmin && catalogo && (
            <button
              onClick={() => setEditando(null)}
              className="ml-auto h-8 px-3 rounded-md bg-stone-900 text-white text-[12px] hover:bg-stone-800 flex items-center gap-1.5"
            >
              <Plus size={13} /> Nueva regla
            </button>
          )}
        </div>

        <div className="divide-y divide-stone-200">
          {visibles.map((r) => (
            <div key={r.codigo} className="flex items-center gap-4 px-4 py-3">
              <span className="font-mono text-[12px] text-stone-500 w-16 shrink-0">{r.codigo}</span>
              <div className="flex-1 min-w-0">
                <p className="text-[13px] text-stone-800 truncate">{r.nombre}</p>
                <p className="text-[11px] text-stone-500 truncate">
                  {r.modulo.replace(/^Módulo \d: /, "")} · {nombreDetector[r.tipo_deteccion] || r.tipo_deteccion} · {r.patrones.length} patrón(es)
                  {!r.predefinida && " · personalizada"}
                </p>
              </div>
              <div className="hidden md:flex gap-1 w-40 shrink-0">
                {[r.owasp_2021, r.owasp_2025].filter(Boolean).map((o) => (
                  <span key={o} className="font-mono text-[10.5px] px-1.5 py-0.5 rounded border border-stone-200 text-stone-600" title={catalogo?.owasp_2021[o] || catalogo?.owasp_2025[o]}>
                    {o}
                  </span>
                ))}
              </div>
              <span className={`text-[11px] w-20 shrink-0 ${SEVERITY_TEXT[r.severidad]}`}>{r.severidad}</span>
              <button
                onClick={() => toggleRegla(r)}
                disabled={!esAdmin}
                className={`text-[12px] shrink-0 w-14 text-right disabled:cursor-default ${r.activa ? "text-emerald-700" : "text-stone-400"}`}
              >
                {r.activa ? "Activa" : "Inactiva"}
              </button>
              <button onClick={() => setEditando(r)} className="text-[12px] shrink-0 w-12 text-right text-stone-600 hover:text-stone-900 underline-offset-2 hover:underline">
                {esAdmin ? "Editar" : "Ver"}
              </button>
            </div>
          ))}
        </div>
      </div>

      {editando !== undefined && catalogo && (
        <RuleEditor
          regla={editando}
          catalogo={catalogo}
          soloLectura={!esAdmin}
          onCerrar={() => setEditando(undefined)}
          onGuardada={onGuardada}
        />
      )}
    </div>
  );
}
