import { useEffect } from "react";
import { createPortal } from "react-dom";

/** Ventana modal con fondo que se desvanece y panel que aparece con escala; Esc la cierra. */
export default function Modal({ onCerrar, children, ancho = "max-w-lg", arriba = false }) {
  useEffect(() => {
    const tecla = (e) => e.key === "Escape" && onCerrar?.();
    window.addEventListener("keydown", tecla);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", tecla);
      document.body.style.overflow = overflow;
    };
  }, [onCerrar]);

  // Se monta en <body> para quedar siempre por encima del encabezado fijo.
  return createPortal(
    <div
      className={`fixed inset-0 z-50 bg-stone-900/40 backdrop-blur-[2px] animate-fade-in flex justify-center overflow-y-auto px-4 ${
        arriba ? "items-start py-8" : "items-center"
      }`}
      onClick={onCerrar}
    >
      <div className={`w-full ${ancho} animate-scale-in`} onClick={(e) => e.stopPropagation()}>
        {children}
      </div>
    </div>,
    document.body
  );
}
