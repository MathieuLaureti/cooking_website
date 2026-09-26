import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig(({ command }) => {
  // Prod is served at https://…/recipes/ behind the homelab reverse proxy; dev stays at /.
  const base = command === 'build' ? '/recipes/' : '/'

  return {
  base,
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      devOptions: { enabled: true },
      includeAssets: ['icon.svg', 'apple-touch-icon.png', 'pwa-192x192.png', 'pwa-512x512.png'],
      manifest: {
        name: 'Cooking',
        short_name: 'Cooking',
        description: 'Ingredient pairings and personal recipe catalog',
        theme_color: '#4A594D',
        background_color: '#4A594D',
        display: 'standalone',
        orientation: 'any',
        start_url: base,
        scope: base,
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2,webmanifest}'],
        navigateFallback: 'index.html',
        navigateFallbackDenylist: [
          /^\/api/,
          /^\/recipes\/api/,
          /^\/mcp/,
          /^\/recipes\/mcp/,
          /^\/oauth/,
          /^\/recipes\/oauth/,
          /^\/\.well-known/,
          /^\/recipes\/\.well-known/,
        ],
      },
    }),
  ],
  server: {
    host: '0.0.0.0',
    port: 6665,
    allowedHosts: true,
    hmr: {
      clientPort: 6665,
    },
    proxy: {
      '/api': {
        target: 'http://server:6666',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  }
})
