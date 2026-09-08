/* 검토중 사업 — 지원할지 말지 따져 보는 단계.

   공고 → 검토중 → (지원완료) → 내 사업
            └ 참여가능 / 부적합·불확실 */
import { request } from "./api";

export type Verdict = "ok" | "no";

export interface Review {
  id: number;
  name: string;
  agency: string;
  amount: number;
  due: string;                 // YYYY-MM-DD, 없으면 ""
  url: string;
  verdict: Verdict;
  /** 부적합·불확실로 둔 까닭. 참여가능이면 빈 값입니다. */
  reason: string;
  note: string;
  announcementId: string | null;
  createdAt: string;
}

export interface ReviewIn {
  name: string;
  agency: string;
  amount: number;
  due: string;
  url: string;
  verdict: Verdict;
  reason: string;
  note: string;
  announcementId?: string | null;
}

export const reviewApi = {
  list: () => request<Review[]>("/api/reviews"),

  create: (body: ReviewIn) =>
    request<Review>("/api/reviews", { method: "POST", body: JSON.stringify(body) }),

  update: (id: number, body: ReviewIn) =>
    request<Review>(`/api/reviews/${id}`, { method: "PUT", body: JSON.stringify(body) }),

  remove: (id: number) =>
    request<void>(`/api/reviews/${id}`, { method: "DELETE" }),
};
