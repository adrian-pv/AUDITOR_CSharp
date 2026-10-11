import { useEffect, useRef, useState } from "react";

/** Número que sube suavemente hasta su valor (al cargar o cambiar el reporte). */
export default function useContador(objetivo, duracion = 700) {
  const [valor, setValor] = useState(objetivo);
  const desde = useRef(0);

  useEffect(() => {
    const reducir = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reducir || typeof objetivo !== "number") {
      setValor(objetivo);
      return;
    }
    const inicio = performance.now();
    const origen = desde.current;
    let marco;
    const paso = (t) => {
      const p = Math.min(1, (t - inicio) / duracion);
      const suave = 1 - Math.pow(1 - p, 3);
      setValor(origen + (objetivo - origen) * suave);
      if (p < 1) marco = requestAnimationFrame(paso);
      else desde.current = objetivo;
    };
    marco = requestAnimationFrame(paso);
    return () => cancelAnimationFrame(marco);
  }, [objetivo, duracion]);

  return valor;
}
