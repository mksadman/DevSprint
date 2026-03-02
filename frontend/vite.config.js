import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api/auth": {
        target: "http://localhost:8001",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/auth/, ""),
      },
      "/api/gateway": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/gateway/, ""),
      },
      "/api/stock": {
        target: "http://localhost:8002",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/stock/, ""),
      },
      "/api/kitchen": {
        target: "http://localhost:8003",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/kitchen/, ""),
      },
      "/api/notification": {
        target: "http://localhost:8004",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/notification/, ""),
      },
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/ws": {
        target: "ws://localhost:8004",
        ws: true,
      },
    },
  },
});
