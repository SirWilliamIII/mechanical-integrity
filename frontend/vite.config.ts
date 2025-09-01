import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
    // Additional module resolution for PrimeVue ecosystem
    extensions: ['.mjs', '.js', '.ts', '.jsx', '.tsx', '.json', '.vue', '.css']
  },
  // Enhanced Vite configuration for reliability
  optimizeDeps: {
    // Force pre-bundling of these dependencies
    include: [
      'vue',
      'vue-router',
      'pinia', 
      'axios',
      'primevue',
      'primeicons/primeicons.css',
      '@primeuix/themes'
    ],
    // Force optimization to avoid cache issues
    force: false  // Will be set to true programmatically if needed
  },
  server: {
    // Enhanced development server configuration
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    // Force dependency optimization on server start
    force: false
  },
  build: {
    // Ensure CommonJS dependencies are handled properly
    commonjsOptions: {
      include: [/node_modules/]
    }
  }
})
