import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: process.env.DEPLOY_RUN_PORT ? Number(process.env.DEPLOY_RUN_PORT) : 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: true,
    port: process.env.DEPLOY_RUN_PORT ? Number(process.env.DEPLOY_RUN_PORT) : 4173,
  },
})
