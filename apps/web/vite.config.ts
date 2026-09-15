import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const API_PROXY_TARGET = "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": API_PROXY_TARGET,
      "/auth": API_PROXY_TARGET,
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
  },
});
