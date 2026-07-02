import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

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
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
    coverage: {
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.{jsx,js}'],
      exclude: [
        'src/main.jsx',
        'src/assets/**',
        'src/components/BgCanvas.jsx',
        'src/components/Bot3D.jsx',
        'src/components/QualityTestPanel.jsx',
        'src/features/ai/components/**',
        'src/features/cronograma/components/**',
        'src/features/propuesta/components/PropuestaWizard.jsx',
        'src/features/propuesta/components/ExcelUploader.jsx',
        'src/features/propuesta/components/PerfilSelector.jsx',
        'src/features/propuesta/components/TorreSelector.jsx',
        'src/features/propuesta/hooks/useExcelParser.js',
        'src/features/propuesta/hooks/usePropuesta.js',
        'src/features/catalogo/components/CatalogoTable.jsx',
      ],
    },
  },
})