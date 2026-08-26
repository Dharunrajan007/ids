import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    // The API's CORS allowlist is exactly localhost/127.0.0.1:5173
    // (ADR-014 notes). strictPort makes Vite FAIL LOUDLY if 5173 is taken
    // instead of silently moving to 5174, where every API call would be
    // blocked by the browser with a confusing CORS error.
    port: 5173,
    strictPort: true,
  },
});
