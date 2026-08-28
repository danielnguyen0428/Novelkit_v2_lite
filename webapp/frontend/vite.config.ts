import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, proxy /api to the FastAPI backend so the SPA and API share an origin.
// The production dist/ is served by the local FastAPI process on the same origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
