/* 서버와 주고받는 부분.
   세션 쿠키를 써야 하므로 credentials:"include" 가 반드시 필요합니다. */

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/* 저장 중 다른 사람이 먼저 저장한 경우.
   조용히 덮어쓰지 않고 이 오류로 올려 보내 화면에서 사람이 정하게 합니다. */
export interface ConflictInfo {
  kind: "exists" | "conflict";
  message: string;
  current: Entry;
}

export class ConflictError extends Error {
  info: ConflictInfo;
  constructor(info: ConflictInfo) {
    super(info.message);
    this.info = info;
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  // headers 는 따로 떼어 합칩니다.
  // ...init 을 headers 뒤에 두면 init.headers 가 Content-Type 을 통째로 지워
  // 서버가 본문을 읽지 못합니다(422). 실제로 그렇게 한 번 깨졌습니다.
  const { headers: extra, ...rest } = init ?? {};
  try {
    res = await fetch(path, {
      credentials: "include",
      ...rest,
      headers: { "Content-Type": "application/json", ...(extra as Record<string, string>) },
    });
  } catch {
    // 서버가 꺼져 있거나 네트워크가 끊긴 경우
    throw new ApiError(0, "서버에 연결하지 못했습니다. 잠시 뒤 다시 시도해 주세요.");
  }

  if (res.status === 409) {
    throw new ConflictError((await res.json()) as ConflictInfo);
  }

  if (!res.ok) {
    let detail = `요청을 처리하지 못했습니다. (${res.status})`;
    try {
      const body = await res.json();
      // 서버 형식 검사(pydantic)가 거르면 detail 이 배열로 옵니다.
      // 그대로 String() 하면 "[object Object]" 가 보이므로 사람이 읽을 말로 바꿉니다.
      if (Array.isArray(body?.detail)) detail = "입력값 형식이 올바르지 않습니다. 숫자 칸에 숫자를 넣었는지 확인해 주세요.";
      else if (body?.detail) detail = String(body.detail);
    } catch {
      /* 본문이 JSON 이 아닌 경우 — 위 기본 문구를 씁니다 */
    }
    throw new ApiError(res.status, detail);
  }

  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

import type { AppSettings, Entry, PeriodOption, ProjectDetail, ProjectSummary } from "./types";

export interface SessionInfo {
  authenticated: boolean;
  using_default_password: boolean;
}

export const api = {
  session: () => request<SessionInfo>("/api/auth/session"),
  projects: () => request<ProjectSummary[]>("/api/projects"),
  project: (id: string) => request<ProjectDetail>(`/api/projects/${encodeURIComponent(id)}`),
  settings: () => request<AppSettings>("/api/settings"),

  // ---- 보고 회차 ----
  periods: (pid: string) =>
    request<PeriodOption[]>(`/api/projects/${encodeURIComponent(pid)}/periods`),

  saveEntry: (pid: string, periodKey: string, payload: SaveEntryBody) =>
    request<{ entry: Entry; project: ProjectDetail }>(
      `/api/projects/${encodeURIComponent(pid)}/entries/${encodeURIComponent(periodKey)}`,
      { method: "PUT", body: JSON.stringify(payload) }
    ),

  deleteEntry: (pid: string, periodKey: string) =>
    request<{ project: ProjectDetail }>(
      `/api/projects/${encodeURIComponent(pid)}/entries/${encodeURIComponent(periodKey)}`,
      { method: "DELETE" }
    ),

  toggleIssue: (pid: string, periodKey: string) =>
    request<{ project: ProjectDetail }>(
      `/api/projects/${encodeURIComponent(pid)}/entries/${encodeURIComponent(periodKey)}/issue-toggle`,
      { method: "POST" }
    ),

  // ---- 입력 패널에서 바로 저장되는 것들 ----
  setStage: (pid: string, stage: number) =>
    request<ProjectDetail>(`/api/projects/${encodeURIComponent(pid)}/stage`,
      { method: "PATCH", body: JSON.stringify({ stage }) }),

  setStageNote: (pid: string, index: number, note: string) =>
    request<ProjectDetail>(`/api/projects/${encodeURIComponent(pid)}/stage-note`,
      { method: "PATCH", body: JSON.stringify({ index, note }) }),

  setTask: (pid: string, index: number, done: boolean) =>
    request<ProjectDetail>(`/api/projects/${encodeURIComponent(pid)}/task`,
      { method: "PATCH", body: JSON.stringify({ index, done }) }),

  // ---- 사업 등록 · 수정 · 삭제 ----
  createProject: (body: ProjectInput) =>
    request<ProjectDetail>("/api/projects", { method: "POST", body: JSON.stringify(body) }),

  updateProject: (id: string, body: ProjectInput) =>
    request<ProjectDetail>(`/api/projects/${encodeURIComponent(id)}`,
      { method: "PUT", body: JSON.stringify(body) }),

  deleteProject: (id: string) =>
    request<{ deleted: string; name: string }>(`/api/projects/${encodeURIComponent(id)}`,
      { method: "DELETE" }),

  setManualUrl: (url: string) =>
    request<{ url: string }>("/api/settings/manual-url",
      { method: "PATCH", body: JSON.stringify({ url }) }),

  // ---- 할 일 ----
  addTodo: (pid: string, text: string, due: string) =>
    request<ProjectDetail>(`/api/projects/${encodeURIComponent(pid)}/todos`,
      { method: "POST", body: JSON.stringify({ text, due }) }),

  toggleTodo: (pid: string, todoId: string) =>
    request<ProjectDetail>(
      `/api/projects/${encodeURIComponent(pid)}/todos/${encodeURIComponent(todoId)}`,
      { method: "PATCH" }),

  removeTodo: (pid: string, todoId: string) =>
    request<ProjectDetail>(
      `/api/projects/${encodeURIComponent(pid)}/todos/${encodeURIComponent(todoId)}`,
      { method: "DELETE" }),
  login: (password: string, remember: boolean) =>
    request<SessionInfo>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ password, remember }),
    }),
  logout: () => request<SessionInfo>("/api/auth/logout", { method: "POST" }),
};

export interface SaveEntryBody {
  spends: { cat: string; amt: number }[];
  kpi: Record<string, number>;
  act: string;
  issue: string;
  plan: string;
  baseVersion: number;
}

export interface ProjectInput {
  name: string;
  agency: string;
  folderUrl: string;
  start: string;
  end: string;
  budget: number;         // 원 단위
  cycle: string;
  kpis: { name: string; target: number; unit: string }[];
  tasks: { name: string }[];
  categories: { name: string; allocated: number }[];
}
