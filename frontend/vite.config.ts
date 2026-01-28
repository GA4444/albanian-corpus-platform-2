import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        // Backend is running with your command on port 8001:
        // python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
        // Use process.env for vite.config.ts (will be available at build time)
        target: process.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
