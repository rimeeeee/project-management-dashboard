/* 서버와 주고받는 부분.
   세션 쿠키를 써야 하므로 credentials:"include" 가 반드시 필요합니다. */

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    // 서버가 꺼져 있거나 네트워크가 끊긴 경우
    throw new ApiError(0, "서버에 연결하지 못했습니다. 잠시 뒤 다시 시도해 주세요.");
  }

  if (!res.ok) {
    let detail = `요청을 처리하지 못했습니다. (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* 본문이 JSON 이 아닌 경우 — 위 기본 문구를 씁니다 */
    }
    throw new ApiError(res.status, detail);
  }

  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export interface SessionInfo {
  authenticated: boolean;
  using_default_password: boolean;
}

export const api = {
  session: () => request<SessionInfo>("/api/auth/session"),
  login: (password: string, remember: boolean) =>
    request<SessionInfo>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ password, remember }),
    }),
  logout: () => request<SessionInfo>("/api/auth/logout", { method: "POST" }),
};
