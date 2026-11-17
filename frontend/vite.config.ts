import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          const locale = id.match(/\/i18n\/locales\/(\w+)\.ts$/)
          if (locale) return `locale-${locale[1]}`
          if (!id.includes('node_modules')) return
          if (id.includes('lightweight-charts')) return 'charts'
          if (id.includes('react-router') || id.includes('/react-dom/') || id.includes('/react/')) return 'react'
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
})
