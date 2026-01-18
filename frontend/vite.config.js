import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 8080,
    strictPort: true,
    allowedHosts: true,
    proxy: {
      '/api': {
         target: 'http://localhost:8383',
         changeOrigin: true,
         rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
