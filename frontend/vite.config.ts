import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Backend routes have no /api/ prefix — proxy each root path directly.
      '/auth': 'http://localhost:8000',
      '/exams': 'http://localhost:8000',
      '/questions': 'http://localhost:8000',
      '/topics': 'http://localhost:8000',
      '/chat': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
