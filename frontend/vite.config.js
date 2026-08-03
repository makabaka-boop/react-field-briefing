import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Frontend dev server on 18110; API calls proxied to backend on 18111.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 18110,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:18111',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.js',
  },
});
