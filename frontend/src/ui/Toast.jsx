import { createContext, useCallback, useContext, useRef, useState } from "react";
import { CheckCircle2, X, XCircle } from "lucide-react";

const ToastContext = createContext(() => {});

/** Notificaciones breves en la esquina inferior derecha que desaparecen solas. */
export function ToastProvider({ children }) {
  const [avisos, setAvisos] = useState([]);
  const siguiente = useRef(0);

  const cerrar = useCallback((id) => setAvisos((a) => a.filter((x) => x.id !== id)), []);

  const mostrar = useCallback(
    (texto, tipo = "ok") => {
      const id = ++siguiente.current;
      setAvisos((a) => [...a.slice(-2), { id, texto, tipo }]);
      setTimeout(() => cerrar(id), tipo === "error" ? 6000 : 3500);
    },
    [cerrar]
  );

  return (
    <ToastContext.Provider value={mostrar}>
      {children}
      <div className="fixed bottom-5 right-5 z-[60] flex flex-col gap-2 w-[min(360px,calc(100vw-2.5rem))]" aria-live="polite">
        {avisos.map((a) => (
          <div
            key={a.id}
            className={`animate-toast-in flex items-start gap-2.5 rounded-lg border bg-white px-3.5 py-3 shadow-lg text-[12.5px] ${
              a.tipo === "error" ? "border-red-200 text-red-800" : "border-emerald-200 text-stone-800"
            }`}
          >
            {a.tipo === "error" ? (
              <XCircle size={16} className="text-red-600 shrink-0 mt-px" />
            ) : (
              <CheckCircle2 size={16} className="text-emerald-600 shrink-0 mt-px" />
            )}
            <span className="flex-1">{a.texto}</span>
            <button onClick={() => cerrar(a.id)} className="text-stone-400 hover:text-stone-700" aria-label="Cerrar aviso">
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
