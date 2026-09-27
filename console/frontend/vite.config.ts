import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vite 配置：dev 代理 /api -> 后端 :8000；prod 走 CORS 白名单。
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
});
