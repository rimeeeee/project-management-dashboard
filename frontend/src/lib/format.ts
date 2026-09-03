/* 표시용 변환 — 프로토타입의 같은 이름 함수를 그대로 옮겼습니다.
   금액은 저장도 입력도 표시도 모두 원 단위입니다.
   전에는 화면에만 억으로 줄여 적었는데, 실제 금액을 바로 읽을 수 없어
   원 단위로 통일했습니다. */

/** 3,800,000,000원 — 단위까지 붙여 줍니다 */
export const fmtMoney = (won: number) =>
  Math.round(won).toLocaleString("ko-KR") + "원";

/** 3,800,000,000 — 단위 없이 숫자만. 뒤에 다른 말을 붙일 때 씁니다 */
export const fmtWon = (won: number) => Math.round(won).toLocaleString("ko-KR");

export const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));

export const pad2 = (n: number) => String(n).padStart(2, "0");

export const isoOf = (d: Date) =>
  `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;

export const mdOf = (d: Date) => `${pad2(d.getMonth() + 1)}.${pad2(d.getDate())}`;

export const todayISO = () => isoOf(new Date());

export function daysBetween(fromISO: string, toISO: string) {
  const a = new Date(fromISO + "T00:00:00");
  const b = new Date(toISO + "T00:00:00");
  return Math.round((b.getTime() - a.getTime()) / 86400000);
}

// 2026-06-01 → 2026.06.01
export const dots = (iso: string) => iso.replaceAll("-", ".");
