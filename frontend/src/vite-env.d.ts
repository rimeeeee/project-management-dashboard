/// <reference types="vite/client" />

/* 빌드할 때 줄 수 있는 설정값.
   VITE_ 로 시작하는 것만 화면 코드에 들어갑니다 (Vite 규칙). */
interface ImportMetaEnv {
  /** API 가 다른 포트에 있을 때 그 포트. 비우면 같은 포트로 봅니다.
      예)  VITE_API_PORT=8081 npm run build   —  src/lib/apiBase.ts 참고 */
  readonly VITE_API_PORT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
