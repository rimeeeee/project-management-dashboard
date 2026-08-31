/* 공고 화면이 서버와 주고받는 부분 */
import { request } from "./api";

export interface AnnStatus {
  key: "upcoming" | "open" | "closed" | "unknown";
  label: string;
  dday: number;
  ddayText: string;
  cls: string;
}

export interface Ann {
  id: string;
  ministry: string;
  agency: string;
  no: string;
  title: string;
  program: string;
  posted: string;
  openFrom: string;
  due: string;
  dueTime: string;
  amount: number;
  contact: string;
  url: string;
  source: string;
  status: AnnStatus;
  keywords: string[];
  fav: boolean;
}

export interface AnnPage {
  items: Ann[];
  total: number;
  page: number;
  pages: number;
  size: number;
  from: number;
  to: number;
  facets: {
    ministries: { name: string; count: number }[];
    tabs: Record<string, number>;
  };
}

export interface CollectorStatus {
  last: null | {
    startedAt: string;
    finishedAt: string;
    ok: boolean;
    trigger: string;
    added: number;
    updated: number;
    totalSeen: number;
    detail: { sources?: { name: string; count: number; truncated: boolean; error: string }[]; kept?: number };
  };
}

export interface AnnInput {
  title: string; ministry: string; agency: string; program: string; no: string;
  posted: string; openFrom: string; due: string; dueTime: string;
  amountEok: number; contact: string; url: string;
}

export const annApi = {
  list: (params: Record<string, string | number>) => {
    const qs = new URLSearchParams(
      Object.entries(params).map(([k, v]) => [k, String(v)])
    ).toString();
    return request<AnnPage>(`/api/announcements?${qs}`);
  },
  toggleFav: (id: string) =>
    request<{ fav: boolean }>(`/api/announcements/${encodeURIComponent(id)}/favorite`, { method: "POST" }),
  create: (body: AnnInput) =>
    request<{ id: string }>("/api/announcements", { method: "POST", body: JSON.stringify(body) }),
  update: (id: string, body: AnnInput) =>
    request<{ id: string }>(`/api/announcements/${encodeURIComponent(id)}`,
      { method: "PUT", body: JSON.stringify(body) }),
  remove: (id: string) =>
    request<{ deleted: string }>(`/api/announcements/${encodeURIComponent(id)}`, { method: "DELETE" }),
  importJson: (announcements: unknown[]) =>
    request<{ added: number; updated: number; kept: number }>("/api/announcements/import",
      { method: "POST", body: JSON.stringify({ announcements }) }),
  setFilter: (body: { include: string[]; ministries: string[]; amount: string }) =>
    request<typeof body>("/api/settings/ann-filter", { method: "PATCH", body: JSON.stringify(body) }),
  collectorStatus: () => request<CollectorStatus>("/api/collector/status"),
  runCollector: () => request<{ totalSeen: number; added: number; updated: number }>(
    "/api/collector/run", { method: "POST" }),
};
