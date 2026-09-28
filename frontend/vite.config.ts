import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Configuration de Vite pour le Front-End éCO2mix React
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Redirection automatique des requêtes /api vers le serveur backend FastAPI
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
