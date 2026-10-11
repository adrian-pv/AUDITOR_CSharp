import { useMemo, useState } from "react";
import { Loader2, X } from "lucide-react";
import { actualizarRegla, crearRegla } from "../api/adminClient";
import ListaChips from "./ListaChips";
import Modal from "../ui/Modal";
import Switch from "../ui/Switch";

const inputCls =
  "w-full h-9 rounded-md border border-stone-300 bg-white px-3 text-[13px] outline-none focus:border-stone-900 focus:ring-1 focus:ring-stone-900 disabled:bg-stone-50 disabled:text-stone-500";

const CATEGORIA_POR_MODULO = {
  "Módulo 1: Seguridad": "Seguridad (OWASP)",
  "Módulo 2: Rendimiento": "Rendimiento (.NET)",
  "Módulo 3: Memoria": "Gestión de Memoria",
  "Módulo 4: Gobierno": "Gobierno Estructural",
};

function valoresPorDefecto(detector) {
  const p = {};
  for (const [k, def] of Object.entries(detector?.parametros || {})) p[k] = def.defecto;
  return p;
}

function Campo({ etiqueta, ayuda, children, className = "" }) {
  return (
    <div className={className}>
      <label className="block text-[12px] font-medium text-stone-700 mb-1.5">{etiqueta}</label>
      {children}
      {ayuda && <p className="text-[11px] text-stone-500 mt-1">{ayuda}</p>}
    </div>
  );
}

/**
 * Crear o editar una regla. Las reglas no se programan: se elige un detector
 * (plantilla) y se le indican patrones y parámetros.
 */
export default function RuleEditor({ regla, catalogo, soloLectura, onCerrar, onGuardada }) {
  const esNueva = !regla;
  const detectores = catalogo.detectores;
  const [datos, setDatos] = useState(() =>
    regla
      ? { ...regla, parametros: { ...valoresPorDefecto(detectores.find((d) => d.tipo === regla.tipo_deteccion)), ...regla.parametros } }
      : {
          nombre: "",
          modulo: catalogo.modulos[0],
          categoria: CATEGORIA_POR_MODULO[catalogo.modulos[0]],
          severidad: "ADVERTENCIA",
          tipo_deteccion: detectores[0].tipo,
          patrones: [],
          parametros: valoresPorDefecto(detectores[0]),
          owasp_2021: "",
          owasp_2025: "",
          cwe: "",
          mensaje: "{detalle}",
          recomendacion: "",
          activa: true,
        }
  );
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  const detector = useMemo(() => detectores.find((d) => d.tipo === datos.tipo_deteccion), [detectores, datos.tipo_deteccion]);
  const set = (campo, valor) => setDatos((d) => ({ ...d, [campo]: valor }));
  const setParam = (campo, valor) => setDatos((d) => ({ ...d, parametros: { ...d.parametros, [campo]: valor } }));

  const cambiarDetector = (tipo) => {
    const det = detectores.find((d) => d.tipo === tipo);
    setDatos((d) => ({ ...d, tipo_deteccion: tipo, parametros: valoresPorDefecto(det) }));
  };

  const guardar = async (e) => {
    e.preventDefault();
    setGuardando(true);
    setError(null);
    const cuerpo = {
      ...datos,
      owasp_2021: datos.owasp_2021 || null,
      owasp_2025: datos.owasp_2025 || null,
      cwe: datos.cwe || null,
    };
    try {
      const r = esNueva ? await crearRegla(cuerpo) : await actualizarRegla(regla.codigo, cuerpo);
      onGuardada(r);
    } catch (err) {
      setError(err.message);
    } finally {
      setGuardando(false);
    }
  };

  const des = soloLectura;

  return (
    <Modal onCerrar={onCerrar} ancho="max-w-3xl" arriba>
      <form onSubmit={guardar} className="w-full bg-white rounded-lg border border-stone-200 shadow-xl">
        <div className="flex items-start justify-between px-6 py-4 border-b border-stone-200">
          <div>
            <p className="text-[15px] font-medium text-stone-900">
              {esNueva ? "Nueva regla" : `${regla.codigo} · ${soloLectura ? "Detalle de la regla" : "Editar regla"}`}
            </p>
            <p className="text-[12px] text-stone-500 mt-0.5">
              {esNueva
                ? "Elija qué tipo de detección usar y escriba qué debe buscar. No requiere programar."
                : regla.predefinida
                ? "Regla de fábrica: puede ajustar sus patrones, severidad y textos."
                : "Regla creada por el Administrador."}
            </p>
          </div>
          <button type="button" onClick={onCerrar} className="text-stone-400 hover:text-stone-700" aria-label="Cerrar">
            <X size={16} />
          </button>
        </div>

        <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2 flex items-center justify-between rounded-md border border-stone-200 bg-stone-50 px-3 py-2.5">
            <div>
              <p className="text-[12.5px] font-medium text-stone-800">Regla activa</p>
              <p className="text-[11px] text-stone-500">Las reglas inactivas no se ofrecen en los análisis.</p>
            </div>
            <Switch checked={datos.activa} onChange={(v) => set("activa", v)} disabled={des} mostrarTexto etiqueta="Regla activa" />
          </div>

          <Campo etiqueta="Nombre de la regla" className="sm:col-span-2">
            <input className={inputCls} value={datos.nombre} onChange={(e) => set("nombre", e.target.value)} required minLength={3} disabled={des} />
          </Campo>

          <Campo etiqueta="Módulo">
            <select
              className={inputCls}
              value={datos.modulo}
              disabled={des}
              onChange={(e) => setDatos((d) => ({ ...d, modulo: e.target.value, categoria: CATEGORIA_POR_MODULO[e.target.value] || d.categoria }))}
            >
              {catalogo.modulos.map((m) => (
                <option key={m}>{m}</option>
              ))}
            </select>
          </Campo>
          <Campo etiqueta="Severidad">
            <select className={inputCls} value={datos.severidad} onChange={(e) => set("severidad", e.target.value)} disabled={des}>
              {catalogo.severidades.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </Campo>

          <Campo etiqueta="OWASP Top 10:2021">
            <select className={inputCls} value={datos.owasp_2021 || ""} onChange={(e) => set("owasp_2021", e.target.value)} disabled={des}>
              <option value="">— Sin categoría —</option>
              {Object.entries(catalogo.owasp_2021).map(([k, v]) => (
                <option key={k} value={k}>{`${k} ${v}`}</option>
              ))}
            </select>
          </Campo>
          <Campo etiqueta="OWASP Top 10:2025">
            <select className={inputCls} value={datos.owasp_2025 || ""} onChange={(e) => set("owasp_2025", e.target.value)} disabled={des}>
              <option value="">— Sin categoría —</option>
              {Object.entries(catalogo.owasp_2025).map(([k, v]) => (
                <option key={k} value={k}>{`${k} ${v}`}</option>
              ))}
            </select>
          </Campo>

          <Campo etiqueta="CWE">
            <input className={inputCls} value={datos.cwe || ""} onChange={(e) => set("cwe", e.target.value)} placeholder="CWE-89" disabled={des} />
          </Campo>
          <Campo etiqueta="Tipo de detección">
            <select
              className={inputCls}
              value={datos.tipo_deteccion}
              onChange={(e) => cambiarDetector(e.target.value)}
              disabled={des || (regla && regla.predefinida)}
            >
              {detectores.map((d) => (
                <option key={d.tipo} value={d.tipo}>{d.nombre}</option>
              ))}
            </select>
          </Campo>

          {detector && (
            <p className="sm:col-span-2 -mt-1 text-[12px] text-stone-600 bg-stone-50 border border-stone-200 rounded-md px-3 py-2">
              {detector.descripcion}
            </p>
          )}

          <Campo
            etiqueta={`Patrones (${datos.patrones.length})`}
            ayuda={detector?.ayuda_patrones}
            className="sm:col-span-2"
          >
            <ListaChips valores={datos.patrones} onChange={(v) => set("patrones", v)} placeholder="Escriba un patrón y presione Enter" deshabilitado={des} />
          </Campo>

          {detector &&
            Object.entries(detector.parametros).map(([nombre, def]) => (
              <Campo key={nombre} etiqueta={nombre.replaceAll("_", " ")} ayuda={def.descripcion} className={def.tipo === "lista" ? "sm:col-span-2" : ""}>
                {def.tipo === "booleano" && (
                  <Switch checked={!!datos.parametros[nombre]} onChange={(v) => setParam(nombre, v)} disabled={des} etiqueta={nombre} />
                )}
                {def.tipo === "opcion" && (
                  <select className={inputCls} value={datos.parametros[nombre] ?? def.defecto} onChange={(e) => setParam(nombre, e.target.value)} disabled={des}>
                    {def.opciones.map((o) => (
                      <option key={o}>{o}</option>
                    ))}
                  </select>
                )}
                {def.tipo === "texto" && (
                  <input className={inputCls} value={datos.parametros[nombre] ?? ""} onChange={(e) => setParam(nombre, e.target.value)} disabled={des} />
                )}
                {def.tipo === "lista" && (
                  <ListaChips valores={datos.parametros[nombre] || []} onChange={(v) => setParam(nombre, v)} placeholder="Agregar…" deshabilitado={des} />
                )}
              </Campo>
            ))}

          <Campo etiqueta="Mensaje del hallazgo" ayuda="{detalle} se reemplaza por lo encontrado (archivo, variable, valor…)." className="sm:col-span-2">
            <textarea className={`${inputCls} h-auto py-2`} rows={2} value={datos.mensaje || ""} onChange={(e) => set("mensaje", e.target.value)} disabled={des} />
          </Campo>
          <Campo etiqueta="Recomendación" className="sm:col-span-2">
            <textarea className={`${inputCls} h-auto py-2`} rows={2} value={datos.recomendacion || ""} onChange={(e) => set("recomendacion", e.target.value)} disabled={des} />
          </Campo>
        </div>

        {error && <p key={error} className="animate-shake mx-6 mb-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-[12.5px] text-red-700">{error}</p>}

        <div className="flex justify-end gap-2 px-6 py-3 border-t border-stone-200">
          <button type="button" onClick={onCerrar} className="h-9 px-4 rounded-md text-[12.5px] text-stone-600 hover:bg-stone-100">
            {des ? "Cerrar" : "Cancelar"}
          </button>
          {!des && (
            <button disabled={guardando} className="btn-press h-9 px-4 rounded-md bg-stone-900 text-white text-[12.5px] hover:bg-stone-800 disabled:opacity-60 flex items-center gap-2">
              {guardando && <Loader2 size={14} className="animate-spin" />}
              {esNueva ? "Crear regla" : "Guardar cambios"}
            </button>
          )}
        </div>
      </form>
    </Modal>
  );
}
