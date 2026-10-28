import { resolve } from 'node:path'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { defineConfig } from 'vite'

// Two separate bundles: sellers never download dashboard code.
// FastAPI serves the built files from dist/ and injects the instance config.
// `--mode demo` (tools/make_demo.py) adds the live demo's stand-in server
// and makes every address relative, for the project page on GitHub Pages.
export default defineConfig(({ mode }) => ({
  plugins: [svelte()],
  base: mode === 'demo' ? './' : '/',
  build: {
    outDir: 'dist',
    // Fonts and images stay separate files: inlined into CSS they would be
    // downloaded on every visit whether the page needs them or not.
    assetsInlineLimit: 0,
    emptyOutDir: true,
    manifest: mode === 'demo',
    rollupOptions: {
      input: {
        form: resolve(import.meta.dirname, 'index.html'),
        dashboard: resolve(import.meta.dirname, 'app/index.html'),
        ...(mode === 'demo'
          ? {
              demo: resolve(import.meta.dirname, 'src/demo/main.ts'),
              brand: resolve(import.meta.dirname, 'src/demo/brand.ts'),
            }
          : {}),
      },
      // The project's static pages import from the brand entry.
      ...(mode === 'demo' ? { preserveEntrySignatures: 'exports-only' as const } : {}),
    },
  },
  server: {
    // During development the HTML comes from Vite and the data from FastAPI.
    proxy: {
      '/api': 'http://localhost:8000',
      '/v': 'http://localhost:8000',
      '/healthz': 'http://localhost:8000',
      // Drawn by the server from the client's color and logo.
      '/app/icons': 'http://localhost:8000',
      '/app/manifest.webmanifest': 'http://localhost:8000',
      '/brand': 'http://localhost:8000',
    },
  },
}))
