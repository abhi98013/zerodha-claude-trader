import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/auth': 'http://localhost:8000',
      '/market': 'http://localhost:8000',
      '/ai': 'http://localhost:8000',
      '/trade': 'http://localhost:8000',
      '/risk': 'http://localhost:8000',
      '/bot': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
  build: {
    outDir: 'build',
  },
});
