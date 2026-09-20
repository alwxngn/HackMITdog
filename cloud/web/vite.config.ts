import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const publicOrigin = loadEnv(mode, process.cwd(), '').VITE_PUBLIC_ORIGIN
  return {
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    strictPort: true, // The tunnel must keep reaching this exact port.
    host: true, // allow tunnel / LAN access
    allowedHosts: publicOrigin ? [new URL(publicOrigin).hostname] : [],
    proxy: {
      '/voice': { target: 'http://127.0.0.1:8000', ws: true },
      '/api': 'http://127.0.0.1:8000',
      '/ws': { target: 'ws://127.0.0.1:8000', ws: true },
    },
  },
  }
})
