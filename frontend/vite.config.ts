import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 后端默认 http://127.0.0.1:8000，接口前缀 /api
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/health': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/docs': { target: 'http://127.0.0.1:8000', changeOrigin: true }
    }
  }
})
