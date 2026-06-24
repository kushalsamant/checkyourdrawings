/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";


export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/compare": "http://127.0.0.1:8000",
      "/jobs": "http://127.0.0.1:8000",
      "/allowance": "http://127.0.0.1:8000",
      "/outputs": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
  test: {
    environment: "jsdom",
  },
});
