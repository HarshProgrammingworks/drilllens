import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8001",
      "/health": "http://127.0.0.1:8001",
      "/ws": { target: "ws://127.0.0.1:8001", ws: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
  },
});
