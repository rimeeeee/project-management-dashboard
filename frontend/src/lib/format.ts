/* 표시용 변환 — 프로토타입의 같은 이름 함수를 그대로 옮겼습니다.
   금액은 원 단위로 저장하고, 여기서만 억으로 바꿔 적습니다. */

export const fmtEok = (won: number) =>
  (won / 1e8).toLocaleString("ko-KR", { maximumFractionDigits: 2 }) + "억";

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
