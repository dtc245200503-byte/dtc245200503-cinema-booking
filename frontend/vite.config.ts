import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Khi phát triển, Vite chuyển /api sang FastAPI để không bị lỗi CORS.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://localhost:8000" } },
});
