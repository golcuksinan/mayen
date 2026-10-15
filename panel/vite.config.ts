import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Çekirdek derlenmiş paneli /panel/ altında sunar (config: panel.dist). Geliştirmede olaylar
// çekirdeğin /events ucundan vekille gelir; çekirdeğin adresi config'teki channel.
export default defineConfig({
  base: '/panel/',
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    proxy: { '/events': { target: 'ws://127.0.0.1:8765', ws: true } },
  },
})
