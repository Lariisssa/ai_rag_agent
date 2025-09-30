import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        // When running in Docker, the backend is reachable at http://backend:8080
        target: process.env.VITE_API_BASE || 'http://backend:8080',
        changeOrigin: true,
      },
      '/media': {
        target: process.env.VITE_API_BASE || 'http://backend:8080',
        changeOrigin: true,
      },
    },
  },
})
