import path from "path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vitest/config"

export default defineConfig({
  plugins: [react(), tailwindcss()],

  resolve: {
    alias: {
      "@": path.resolve(process.cwd(), "./src"),
    },
  },

  // Retry-policy tests are pure logic (mocked fetch, fake timers), so the
  // default node environment is enough - no jsdom dependency needed.
  test: {
    environment: "node",
  },

  /**
   * Waypoint uses 5174 deliberately because 5173 is reserved for
   * the GlaucomaAI frontend during local development.
   *
   * strictPort prevents Vite from silently switching ports, which would
   * otherwise break the backend CORS allowlist.
   */
  server: {
    port: 5174,
    strictPort: true,
  },
})