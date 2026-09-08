/* 회의록 — 사업비 지출 증빙(감사·정산)에 쓰는 문서.
   사업에 매달려 있어서 주소도 사업 아래로 들어갑니다. */
import { request } from "./api";

export interface MeetingPhoto {
  id: number;
  name: string;
  url: string;
}

export interface Meeting {
  id: number;
  title: string;
  metOn: string;              // YYYY-MM-DD
  place: string;
  attendees: string[];
  bullets: string[];
  memo: string;
  amount: number;            // 원, 0 이면 금액 없음
  /* 파일 이름은 서버가 정합니다. 화면에서 따로 만들면 미리 본 이름과
     실제로 받은 파일 이름이 달라집니다. */
  fileName: string;
  createdAt: string;
  photos: MeetingPhoto[];
}

export interface MeetingIn {
  title: string;
  metOn: string;
  place: string;
  attendees: string[];
  bullets: string[];
  memo: string;
  amount: number;
}

const base = (pid: string) => `/api/projects/${encodeURIComponent(pid)}/meetings`;

export const meetingApi = {
  list: (pid: string) => request<Meeting[]>(base(pid)),

  create: (pid: string, body: MeetingIn) =>
    request<Meeting>(base(pid), { method: "POST", body: JSON.stringify(body) }),

  update: (pid: string, id: number, body: MeetingIn) =>
    request<Meeting>(`${base(pid)}/${id}`, { method: "PUT", body: JSON.stringify(body) }),

  remove: (pid: string, id: number) =>
    request<void>(`${base(pid)}/${id}`, { method: "DELETE" }),

  /* AI 초안. 저장하지 않고 결과만 돌려줍니다 — 사람이 고친 뒤 저장해야
     남습니다. 손대기 전 글이 그대로 문서에 들어가지 않게 하려는 것입니다. */
  draft: (pid: string, body: { title: string; memo: string; place: string }) =>
    request<{ bullets: string[] }>(`${base(pid)}/draft`, {
      method: "POST", body: JSON.stringify(body),
    }),

  titleSuggestions: (pid: string, title: string) =>
    request<{ titles: string[] }>(`${base(pid)}/title-suggestions`, {
      method: "POST", body: JSON.stringify({ title, memo: "", place: "" }),
    }),

  /* 사진은 JSON 이 아니라 FormData 로 보냅니다. request() 는 Content-Type 을
     application/json 으로 박아 두므로 여기서는 fetch 를 직접 씁니다 —
     multipart 는 브라우저가 경계 문자열까지 넣어 헤더를 만들어야 합니다. */
  async uploadPhoto(pid: string, id: number, file: File): Promise<MeetingPhoto> {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${base(pid)}/${id}/photos`, {
      method: "POST", credentials: "include", body: fd,
    });
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      throw new Error(d.detail || "사진을 올리지 못했습니다.");
    }
    return res.json();
  },

  removePhoto: (pid: string, id: number, photoId: number) =>
    request<void>(`${base(pid)}/${id}/photos/${photoId}`, { method: "DELETE" }),

  docxUrl: (pid: string, id: number) => `${base(pid)}/${id}/docx`,
};
