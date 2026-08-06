import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 개발 서버에서는 /api 를 게이트웨이(I-1)로 넘김.
// 프런트는 I-2·I-3을 직접 부르지 않음 — 진입 지점은 I-1 하나뿐임(⑦ 3절).
export default defineConfig({
  // plugins가 빠지면 JSX가 classic 변환으로 남아 런타임에
  // `ReferenceError: React is not defined`로 죽음(빌드는 통과함).
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': { target: 'http://localhost:8080', changeOrigin: true } },
  },
  build: { outDir: 'dist' },
})
