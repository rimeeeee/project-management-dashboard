/* 화면 테마 — 프로토타입의 currentTheme() / toggleTheme() 을 그대로 옮겼습니다.
   저장 키(bizDash.v3.theme)도 같은 것을 씁니다. */
const STORE_KEY = "bizDash.v3";

export type Theme = "light" | "dark";

export function currentTheme(): Theme {
  const stamped = document.documentElement.getAttribute("data-theme");
  if (stamped === "light" || stamped === "dark") return stamped;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function toggleTheme(): Theme {
  const next: Theme = currentTheme() === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  try {
    localStorage.setItem(STORE_KEY + ".theme", next);
  } catch {
    /* 프라이빗 모드 — 이번 방문에만 적용됩니다 */
  }
  return next;
}

// 버튼에 적을 글자. 프로토타입 syncThemeBtn() 과 같은 문구입니다.
export const themeButtonLabel = (t: Theme) =>
  t === "dark" ? "밝은 화면으로" : "어두운 화면으로";
