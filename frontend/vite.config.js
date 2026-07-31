import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Proxies /api and /images to the FastAPI backend during development
// so the frontend can just call relative paths like fetch("/api/chat")
// without worrying about CORS or hardcoded hosts/ports.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // listen on 0.0.0.0 so LAN devices (e.g. your phone) can connect
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/images": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
