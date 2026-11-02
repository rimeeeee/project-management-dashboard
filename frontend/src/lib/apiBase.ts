/* API 가 어느 주소에 있는지 정하는 곳.

   한 포트로 쓸 때(기본)는 빈 문자열입니다. 그러면 "/api/..." 가 그대로
   상대 주소가 되어, 화면을 내보낸 서버에 그대로 묻습니다.

   프론트와 백엔드를 다른 포트로 나눌 때는 빌드할 때 VITE_API_PORT 를 줍니다.
   예)  VITE_API_PORT=8081 npm run build

   서버 IP 를 박아 넣지 않고 포트만 받는 이유는, 보는 사람이 어떤 주소로
   들어왔든(IP·호스트이름·localhost) 그 주소의 다른 포트를 보게 하려는
   것입니다. 서버 IP 가 바뀌어도 다시 빌드하지 않아도 됩니다. */

const port = import.meta.env.VITE_API_PORT?.trim();

function compute(): string {
  if (!port) return "";
  // 브라우저가 아닌 곳(테스트 등)에서 불릴 수 있어 확인합니다.
  if (typeof window === "undefined") return "";
  const { protocol, hostname, port: here } = window.location;
  // 같은 포트면 상대 주소가 낫습니다 — 괜히 절대 주소로 만들면
  // CORS 심사를 타지 않아도 될 요청이 타게 됩니다.
  const nowPort = here || (protocol === "https:" ? "443" : "80");
  if (nowPort === port) return "";
  return `${protocol}//${hostname}:${port}`;
}

/** API 주소 앞에 붙일 것. 한 포트로 쓸 때는 "" 입니다. */
export const API_BASE = compute();

/** "/api/..." 를 실제로 요청할 주소로 바꿉니다. */
export function apiUrl(path: string): string {
  // 이미 절대 주소면 그대로 둡니다.
  if (/^https?:\/\//i.test(path)) return path;
  return API_BASE + path;
}
