import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// En desarrollo, /api se envía al backend local (python dev_server.py, puerto 8000).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': 'http://localhost:8000' } },
  build: { outDir: 'dist', sourcemap: false },
});
