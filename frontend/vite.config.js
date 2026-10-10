import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Durante desarrollo, el backend expone reporte.json en esta ruta
      // (ver backend/main.py). En producción el frontend puede leer el
      // archivo servido estáticamente o vía un endpoint HTTP simple.
      "/api": "http://localhost:8000",
    },
  },
});
