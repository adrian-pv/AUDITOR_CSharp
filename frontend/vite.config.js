import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Durante desarrollo, todas las peticiones a /api se reenvían al
      // backend (python server.py). Se usa 127.0.0.1 y no "localhost"
      // porque en Windows "localhost" puede resolverse a IPv6 (::1) y el
      // servidor solo escucha en IPv4.
      "/api": "http://127.0.0.1:8000",
    },
  },
});
