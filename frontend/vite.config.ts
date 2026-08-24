import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  server: {
    port: 3000,
    host: true,
  },
  preview: {
    host: '127.0.0.1',
    port: 3001,
    allowedHosts: ['novakai.net', 'www.novakai.net'],
  },
})
