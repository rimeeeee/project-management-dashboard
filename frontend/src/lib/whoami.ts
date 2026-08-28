/* 입력자 이름.

   담당자 계정을 두지 않기로 해서, 누가 입력했는지는 화면에서 적은 이름으로
   남깁니다. 한 번 적으면 이 브라우저에 기억되어 다음부터 자동으로 채워집니다.

   나중에 사내 계정을 붙이면 이 파일과 서버의 entered_by() 만 바꾸면 되고,
   나머지 코드는 손대지 않아도 됩니다. */
const KEY = "bizDash.v3.enteredBy";

export function getWhoami(): string {
  try {
    return localStorage.getItem(KEY) || "";
  } catch {
    return "";
  }
}

export function setWhoami(name: string): void {
  try {
    localStorage.setItem(KEY, name.trim());
  } catch {
    /* 프라이빗 모드 — 이번 방문에만 적용됩니다 */
  }
}

/* HTTP 머리말은 latin-1 만 담을 수 있어서 한글 이름을 그대로 넣으면 깨집니다.
   ('김담당' → 'ê¹ë´ë¹')  서버에서 unquote 로 풉니다. */
export function whoHeader(name: string): Record<string, string> {
  return { "X-Entered-By": encodeURIComponent(name.trim()) };
}
