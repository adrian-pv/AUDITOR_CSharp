import { Loader2 } from "lucide-react";

/**
 * Interruptor encendido/apagado: verde cuando está activo, gris cuando no.
 * Accesible (role="switch", teclado) y con estado de carga mientras se guarda.
 */
export default function Switch({ checked, onChange, disabled = false, cargando = false, etiqueta, tamano = "md", mostrarTexto = false, textos = ["Activa", "Inactiva"] }) {
  const md = tamano === "md";
  const pista = md ? "w-10 h-6" : "w-8 h-[18px]";
  const perilla = md ? "w-5 h-5" : "w-[14px] h-[14px]";
  const recorrido = md ? "translate-x-4" : "translate-x-[14px]";

  return (
    <span className="inline-flex items-center gap-2">
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={etiqueta}
        title={etiqueta}
        disabled={disabled || cargando}
        onClick={() => onChange?.(!checked)}
        className={`relative shrink-0 rounded-full transition-colors duration-200 ease-out outline-none
          focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-emerald-500
          ${pista} ${checked ? "bg-emerald-600" : "bg-stone-300"}
          ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer hover:brightness-95"}`}
      >
        <span
          className={`absolute top-0.5 left-0.5 ${perilla} rounded-full bg-white shadow-sm flex items-center justify-center
            transition-transform duration-200 ease-[cubic-bezier(.2,.8,.2,1)] ${checked ? recorrido : "translate-x-0"}`}
        >
          {cargando && <Loader2 size={md ? 12 : 10} className="animate-spin text-stone-400" />}
        </span>
      </button>
      {mostrarTexto && (
        <span className={`text-[12px] w-14 transition-colors duration-200 ${checked ? "text-emerald-700" : "text-stone-400"}`}>
          {checked ? textos[0] : textos[1]}
        </span>
      )}
    </span>
  );
}
