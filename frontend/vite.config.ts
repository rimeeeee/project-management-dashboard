import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // 개발 중 /api 로 가는 요청은 백엔드(8000)로 넘깁니다.
    // 같은 주소에서 오가는 것처럼 보이게 해야 세션 쿠키가 정상 동작합니다.
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
