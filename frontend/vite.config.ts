import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/status': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/performance': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/trades': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/positions': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/logs': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/backtest': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/live': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true
      }
    }
  }
})