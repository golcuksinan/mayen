import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Ekran, panelin görsel dilini (tema, hareket, parçalar) panelin kaynağından alır; iki arayüz
// aynı dosyayı okur, kopya ayrışamaz. Ortak dosyalar bu projenin React'ini kullanır (dedupe):
// iki ayrı React, kancaları bozardı. Derlenmiş dosyalar göreli yolla açılır (pywebview).
export default defineConfig({
  base: './',
  plugins: [react()],
  resolve: { dedupe: ['react', 'react-dom', 'motion'] },
  server: { host: '127.0.0.1', port: 5174, fs: { allow: ['..'] } },
})
