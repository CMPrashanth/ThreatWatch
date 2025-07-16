import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  // This section forces Vite to pre-bundle these specific libraries,
  // which resolves complex dependency issues with the recharts library.
  optimizeDeps: {
    include: ['recharts', 'react-is', 'lodash'],
  },
})
