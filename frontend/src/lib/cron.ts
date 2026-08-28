/* 수집 주기를 사람이 읽는 말로 바꿉니다.

   화면에 '0 6 * * 1,4' 라고 적혀 있으면 크론 표기를 아는 사람만 읽을 수 있습니다.
   이 대시보드를 쓰는 분들이 볼 화면이므로 '매주 월·목 오전 6시' 로 적습니다.
   (설정값 자체는 .env 의 COLLECTOR_CRON 그대로 둡니다.)

   해석하지 못하는 표기가 들어오면 원래 값을 그대로 보여 줍니다.
   틀리게 읽어 주는 것보다 낫습니다. */

const DAYS = ["일", "월", "화", "수", "목", "금", "토"];

function hourText(h: number, m: number): string {
  // 0시를 '오전 12시'로 적으면 헷갈립니다
  if (m === 0 && h === 0) return "자정";
  if (m === 0 && h === 12) return "정오";
  const ampm = h < 12 ? "오전" : "오후";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return m === 0 ? `${ampm} ${h12}시` : `${ampm} ${h12}시 ${m}분`;
}

export function describeCron(cron: string): string {
  const parts = (cron || "").trim().split(/\s+/);
  if (parts.length !== 5) return cron;
  const [min, hour, dom, mon, dow] = parts;

  // 분·시는 숫자 하나일 때만 읽습니다 (*/10 같은 표기는 그대로 보여 줍니다)
  if (!/^\d{1,2}$/.test(min) || !/^\d{1,2}$/.test(hour)) return cron;
  const m = Number(min);
  const h = Number(hour);
  if (m > 59 || h > 23) return cron;
  const time = hourText(h, m);

  if (mon !== "*") return cron;

  // 매일
  if (dom === "*" && (dow === "*" || dow === "?")) return `매일 ${time}`;

  // 요일 지정 — 1,4 또는 1-5
  if (dom === "*" && /^[0-7](([,-][0-7])*)$/.test(dow)) {
    let nums: number[];
    if (dow.includes("-")) {
      const [a, b] = dow.split("-").map(Number);
      if (a > b) return cron;
      nums = Array.from({ length: b - a + 1 }, (_, i) => a + i);
    } else {
      nums = dow.split(",").map(Number);
    }
    // 크론은 0 과 7 을 모두 일요일로 씁니다
    const names = [...new Set(nums.map((n) => DAYS[n === 7 ? 0 : n]))];
    if (!names.length) return cron;
    return `매주 ${names.join("·")} ${time}`;
  }

  // 매월 특정 날짜
  if (/^\d{1,2}$/.test(dom) && (dow === "*" || dow === "?")) {
    return `매월 ${Number(dom)}일 ${time}`;
  }

  return cron;
}
