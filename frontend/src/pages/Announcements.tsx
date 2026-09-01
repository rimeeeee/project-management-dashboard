/* 사업 현황 (공고) — 프로토타입 renderAnn() 을 옮겼습니다.

   프로토타입과 달라지는 점은 '걸러내기와 정렬을 서버에서 한다'는 것뿐입니다.
   판단 기준(접수예정/접수중/마감, 금액 구간, 키워드를 제목·사업명에만 맞춤,
   마감 임박순 묶음 순서)은 그대로입니다.

   NTIS 통합공고를 붙이면 전 부처라 수천 건이 됩니다. 그만큼을 브라우저로
   내려보낼 수 없어 한 쪽씩(기본 40건) 받습니다. */
import { useCallback, useEffect, useRef, useState } from "react";
import Pager from "../components/Pager";
import { annApi, type Ann, type AnnPage, type CollectorStatus } from "../lib/annApi";
import { fmtEok } from "../lib/format";
import type { AppSettings } from "../lib/types";
import "../styles/pager.css";

const SIZE_KEY = "bizDash.v3.annPageSize";
const VIEW_KEY = "bizDash.v3.annView";      // card | list

const TABS: { key: string; label: string }[] = [
  { key: "all", label: "전체" },
  { key: "upcoming", label: "접수예정" },
  { key: "open", label: "접수중" },
  { key: "closed", label: "마감" },
  { key: "fav", label: "관심" },
];

const dots = (iso: string) => iso.replaceAll("-", ".");

interface Props {
  settings: AppSettings;
  onSettings: (s: AppSettings) => void;
  onModal: (msg: string, sub?: string, onOk?: () => void, danger?: boolean) => void;
  onEditAnn: (a: Ann | null) => void;
  // 공고를 '내 사업'으로 옮겨 등록 화면을 채웁니다
  onToProject: (a: Ann) => void;
  // 공고 추가 폼의 '부처' 자동완성에 쓰라고 위로 올려 줍니다
  onFacets: (ministries: string[]) => void;
  reloadToken: number;          // 등록·수정·불러오기 뒤 목록을 다시 받게 하는 값
}

export default function Announcements({
  settings, onSettings, onModal, onEditAnn, onToProject, onFacets, reloadToken,
}: Props) {
  const f = settings.ann_filter;
  const [data, setData] = useState<AnnPage | null>(null);
  const [collector, setCollector] = useState<CollectorStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const [tab, setTab] = useState("all");
  const [query, setQuery] = useState("");
  // 기본은 공고일 최신순입니다. 화면을 열었을 때 새로 올라온 공고부터 보이는 편이
  // 실제로 쓰는 순서에 맞습니다.
  const [sort, setSort] = useState("posted");
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(() => {
    try {
      const v = Number(localStorage.getItem(SIZE_KEY));
      return [20, 40, 60].includes(v) ? v : 40;
    } catch {
      return 40;   // 프라이빗 모드 — 기본값으로 동작합니다
    }
  });
  // 카드로 볼지 목록으로 볼지. 공고가 수백 건이라 훑을 때는 목록이 편하고,
  // 하나씩 자세히 볼 때는 카드가 편해서 둘 다 둡니다. 고른 것은 기억해 둡니다.
  const [view, setView] = useState<"card" | "list">(() => {
    try {
      return localStorage.getItem(VIEW_KEY) === "list" ? "list" : "card";
    } catch {
      return "card";   // 프라이빗 모드 — 기본값으로 동작합니다
    }
  });
  const changeView = (v: "card" | "list") => {
    setView(v);
    try { localStorage.setItem(VIEW_KEY, v); } catch { /* 프라이빗 모드 */ }
  };

  // 조건 입력칸은 타이핑 중일 수 있어 따로 들고 있다가 [적용]에서 넘깁니다
  const [includeText, setIncludeText] = useState(f.include.join(", "));

  const load = useCallback(async () => {
    try {
      const r = await annApi.list({
        tab, q: query, sort, page, size,
        ministries: f.ministries.join(","),
        amount: f.amount,
        include: f.include.join(","),
      });
      setData(r);
      onFacets(r.facets.ministries.map((m) => m.name));
      setErr("");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "공고를 불러오지 못했습니다.");
    }
  }, [tab, query, sort, page, size, f.ministries, f.amount, f.include, onFacets]);

  useEffect(() => { void load(); }, [load, reloadToken]);
  useEffect(() => { annApi.collectorStatus().then(setCollector).catch(() => {}); }, [reloadToken]);

  // 조건·탭·검색을 바꾸면 1쪽으로 돌아갑니다
  useEffect(() => { setPage(1); }, [tab, query, sort, size, f.ministries, f.amount, f.include]);

  /* 쪽을 넘기면 목록 맨 위부터 보이게 올려 줍니다.
     쪽 번호가 목록 아래에 있어서, 누른 자리에 그대로 있으면 새 목록의 끝을
     보고 있게 됩니다.

     여기서 바로 올리면 안 됩니다. 새 목록을 아직 그리기 전이라 화면 길이가
     바뀌면서 이동이 취소됩니다(실제로 그렇게 안 올라갔습니다).
     그래서 새 목록이 그려진 뒤에 올립니다. */
  const scrollAfterLoad = useRef(false);

  function goPage(p: number) {
    scrollAfterLoad.current = true;
    setPage(p);
  }

  useEffect(() => {
    if (!data || !scrollAfterLoad.current) return;
    scrollAfterLoad.current = false;
    window.scrollTo({ top: 0 });
  }, [data]);

  async function saveFilter(next: Partial<AppSettings["ann_filter"]>) {
    const body = { include: f.include, ministries: f.ministries, amount: f.amount, ...next };
    try {
      const saved = await annApi.setFilter(body);
      onSettings({ ...settings, ann_filter: saved });
    } catch (e) {
      setErr(e instanceof Error ? e.message : "조건을 저장하지 못했습니다.");
    }
  }

  async function runCollector() {
    setBusy(true);
    try {
      const r = await annApi.runCollector();
      onModal("수집했습니다", `총 ${r.totalSeen}건 · 새 공고 ${r.added}건 · 갱신 ${r.updated}건`);
      await load();
      setCollector(await annApi.collectorStatus());
    } catch (e) {
      onModal("수집하지 못했습니다", e instanceof Error ? e.message : "");
    } finally {
      setBusy(false);
    }
  }

  async function toggleFav(a: Ann) {
    try {
      await annApi.toggleFav(a.id);
      await load();
    } catch { /* 목록을 다시 받으면 맞춰집니다 */ }
  }

  function removeAnn(a: Ann) {
    onModal("이 공고를 삭제할까요?", a.title, async () => {
      await annApi.remove(a.id);
      await load();
    }, true);
  }

  const last = collector?.last;
  const 마지막수집 = last
    ? `${last.startedAt.slice(5, 16).replace("T", " ").replace("-", "/")} · ${last.totalSeen}건`
    : "아직 없음";
  // 어느 서버가 끊겼는지 같은 내부 사정은 쓰는 사람에게 의미가 없어 적지 않습니다.
  // 다만 그런 일이 있었다는 것은 점 색깔로만 남겨 둡니다.
  const 문제있음 =
    (last?.detail?.sources?.some((s) => s.truncated) ?? false) ||
    (last?.detail?.sources?.some((s) => s.error) ?? false);

  return (
    <section className="view on">
      <div className="page-title" id="annTop">사업 현황 — 대외 공고</div>

      {/* 수집이 조용히 멈춰 있는 걸 모르는 게 제일 위험합니다 */}
      <div className="collect-bar">
        <span className={"dot" + (last ? (문제있음 ? " stale" : "") : " none")} />
        <span>마지막 수집 <b style={{ color: "var(--ink-2)" }}>{마지막수집}</b></span>
        <span className="spacer" />
        <button type="button" className="mini-btn" onClick={runCollector} disabled={busy}>
          {busy ? "수집 중…" : "지금 수집"}
        </button>
        <button type="button" className="btn-add-ann" style={{ marginLeft: 0 }}
                onClick={() => onEditAnn(null)}>+ 공고 추가</button>
      </div>

      <div className="card filter-card">
        <h2>관심 조건 <span className="hint">
          <button type="button" className="mini-btn"
                  onClick={() => { setIncludeText(""); void saveFilter({ include: [], ministries: [], amount: "all" }); }}>
            조건 초기화
          </button>
        </span></h2>
        <div className="filter-grid">
          <div className="f">
            <label htmlFor="fInc">포함 키워드</label>
            <input id="fInc" placeholder="예: 병원, 의료, 임상" value={includeText}
                   onChange={(e) => setIncludeText(e.target.value)}
                   onBlur={() => void saveFilter({
                     include: includeText.split(",").map((x) => x.trim()).filter(Boolean),
                   })}
                   onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }} />
          </div>
          <div className="f">
            <label htmlFor="fAmt">공고금액</label>
            <select id="fAmt" value={f.amount} onChange={(e) => void saveFilter({ amount: e.target.value })}>
              <option value="all">전체</option>
              <option value="lt1">1억 미만</option>
              <option value="1to3">1억 이상 ~ 3억 미만</option>
              <option value="3to5">3억 이상 ~ 5억 미만</option>
              <option value="gte5">5억 이상</option>
            </select>
          </div>
        </div>
        <div className="f" style={{ marginTop: 14 }}>
          <label>부처</label>
          <div className="chips" id="fMinistries">
            {(data?.facets.ministries ?? []).map((m) => (
              <button key={m.name} type="button"
                      className={"chip" + (f.ministries.includes(m.name) ? " on" : "")}
                      onClick={() => void saveFilter({
                        ministries: f.ministries.includes(m.name)
                          ? f.ministries.filter((x) => x !== m.name)
                          : [...f.ministries, m.name],
                      })}>
                {m.name} {m.count}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="ann-bar">
        <div className="tabs" id="annTabs">
          {TABS.map((t) => (
            <button key={t.key} type="button" className={"tab" + (tab === t.key ? " on" : "")}
                    onClick={() => setTab(t.key)}>
              {t.label} {data?.facets.tabs[t.key] ?? 0}
            </button>
          ))}
        </div>
        <input id="annQuery" className="ann-q" placeholder="제목 내 검색"
               value={query} onChange={(e) => setQuery(e.target.value)} />
        <select id="annSort" className="ann-sort" aria-label="공고 정렬 기준"
                value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="posted">공고일 최신순</option>
          <option value="due">마감 임박순</option>
          <option value="amount">공고금액 큰순</option>
          <option value="score">관련도순</option>
        </select>
        <div className="view-toggle" role="group" aria-label="보기 방식">
          <button type="button" className={"vt" + (view === "card" ? " on" : "")}
                  onClick={() => changeView("card")}
                  title="카드로 보기" aria-label="카드로 보기" aria-pressed={view === "card"}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <rect x="3" y="3" width="7" height="7" rx="1" />
              <rect x="14" y="3" width="7" height="7" rx="1" />
              <rect x="3" y="14" width="7" height="7" rx="1" />
              <rect x="14" y="14" width="7" height="7" rx="1" />
            </svg>
          </button>
          <button type="button" className={"vt" + (view === "list" ? " on" : "")}
                  onClick={() => changeView("list")}
                  title="목록으로 보기" aria-label="목록으로 보기" aria-pressed={view === "list"}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <line x1="8" y1="6" x2="21" y2="6" />
              <line x1="8" y1="12" x2="21" y2="12" />
              <line x1="8" y1="18" x2="21" y2="18" />
              <line x1="3" y1="6" x2="3.01" y2="6" />
              <line x1="3" y1="12" x2="3.01" y2="12" />
              <line x1="3" y1="18" x2="3.01" y2="18" />
            </svg>
          </button>
        </div>
      </div>

      <div className="ann-count" id="annCount">
        {data && (data.total
          ? <span>전체 <b>{data.total.toLocaleString()}건</b> 중 {data.from.toLocaleString()} – {data.to.toLocaleString()}번째</span>
          : (data.facets.tabs.all === 0 && !collector?.last
              // 처음 켠 상태 — 조건 문제가 아니라 아직 한 번도 안 받아온 것입니다
              ? <span>아직 공고를 받아온 적이 없습니다. 위의 [지금 수집]을 눌러 주세요.</span>
              : <span>조건에 맞는 공고가 없습니다</span>))}
        <span className="size">
          <label htmlFor="annSize">쪽당</label>
          <select id="annSize" value={size}
                  onChange={(e) => { const v = Number(e.target.value); setSize(v);
                    try { localStorage.setItem(SIZE_KEY, String(v)); } catch { /* 프라이빗 모드 */ } }}>
            <option value={20}>20개</option>
            <option value={40}>40개</option>
            <option value={60}>60개</option>
          </select>
        </span>
      </div>

      {err && <div className="form-err on">{err}</div>}

      {view === "list" && (
        <div className="card ann-list">
          <div className="tbl-wrap"><table className="tbl">
            <thead><tr>
              <th style={{ width: 96 }}>상태</th>
              <th style={{ width: 150 }}>발주처</th>
              <th>공고명</th>
              <th style={{ width: 170 }}>접수기간</th>
              <th className="num" style={{ width: 110 }}>공고금액</th>
              <th style={{ width: 190 }}></th>
            </tr></thead>
            <tbody>
              {data?.items.length ? data.items.map((a) => (
                <tr key={a.id}>
                  <td>
                    <span className={"st st-" + a.status.key}>{a.status.label}</span>
                    <div className={"dday " + a.status.cls} style={{ marginTop: 2 }}>{a.status.ddayText}</div>
                  </td>
                  <td className="cellsub">{a.ministry}</td>
                  <td>
                    {a.url
                      ? <a href={a.url} target="_blank" rel="noopener noreferrer">{a.title} ↗</a>
                      : a.title}
                    {a.source === "manual" && <span className="src-tag" style={{ marginLeft: 6 }}>직접 등록</span>}
                    {a.program && <div className="home-sub">{a.program}</div>}
                  </td>
                  <td className="cellsub">
                    {a.due
                      ? <>{dots(a.openFrom)}<br />~ {dots(a.due)} {a.dueTime}</>
                      : <span style={{ color: "var(--muted)" }}>미확인</span>}
                  </td>
                  <td className="num cellnum">{a.amount ? fmtEok(a.amount) + "원" : "-"}</td>
                  <td>
                    <div className="ann-acts">
                      <button type="button" className={"star" + (a.fav ? " on" : "")}
                              onClick={() => toggleFav(a)}>{a.fav ? "★" : "☆"}</button>
                      <button type="button" className="mini-btn" onClick={() => onToProject(a)}>사업 등록</button>
                      <button type="button" className="mini-btn" onClick={() => onEditAnn(a)}>수정</button>
                      {a.source === "manual" && (
                        <button type="button" className="mini-btn danger" onClick={() => removeAnn(a)}>삭제</button>
                      )}
                    </div>
                  </td>
                </tr>
              )) : (
                !data && <tr><td colSpan={6}><div className="empty">불러오는 중입니다.</div></td></tr>
              )}
            </tbody>
          </table></div>
        </div>
      )}

      <div className="ann-grid" id="annGrid" hidden={view === "list"}>
        {data?.items.length ? data.items.map((a) => (
          <article key={a.id} className="ann">
            <div className="top">
              <span className="src">{a.ministry}</span>
              <span className={"st st-" + a.status.key}>{a.status.label}</span>
              <span className={"dday " + a.status.cls}>{a.status.ddayText}</span>
            </div>
            <h3>{a.url
              ? <a href={a.url} target="_blank" rel="noopener noreferrer">{a.title} ↗</a>
              : a.title}</h3>
            {a.keywords.length > 0 && (
              <div className="kw-row">{a.keywords.map((k) => <span key={k} className="kw">{k}</span>)}</div>
            )}
            <div className="kv">
              <div><span className="k">접수기간</span><span className="v">
                {a.due
                  ? `${dots(a.openFrom)} ~ ${dots(a.due)} ${a.dueTime}`
                  : <span style={{ color: "var(--muted)", fontWeight: 400 }}>미확인 · 원문에서 확인</span>}
              </span></div>
              <div><span className="k">공고금액</span><span className="v">{a.amount ? fmtEok(a.amount) + "원" : "-"}</span></div>
              <div><span className="k">전문기관</span><span className="v" title={a.agency}>{a.agency || "-"}</span></div>
              <div><span className="k">사업명</span><span className="v" title={a.program}>{a.program || "-"}</span></div>
            </div>
            <div className="foot2">
              <div className="foot-meta">
                <span>{a.no || "-"}</span>
                {a.source === "manual" && <span className="src-tag">직접 등록</span>}
              </div>
              <div className="ann-acts">
                <button type="button" className={"star" + (a.fav ? " on" : "")}
                        onClick={() => toggleFav(a)}>{a.fav ? "★ 관심" : "☆ 관심"}</button>
                <button type="button" className="mini-btn" onClick={() => onToProject(a)}>사업 등록</button>
                <button type="button" className="mini-btn" onClick={() => onEditAnn(a)}>수정</button>
                {/* 수집된 공고는 지워도 다음 수집 때 되살아나므로 삭제 버튼을 두지
                    않습니다 (기관 목록에 있는 한 다시 들어옵니다). 삭제는 직접
                    등록·수정해서 '직접 등록' 표가 붙은 공고에만 보입니다. */}
                {a.source === "manual" && (
                  <button type="button" className="mini-btn danger" onClick={() => removeAnn(a)}>삭제</button>
                )}
              </div>
            </div>
          </article>
        )) : (
          // 공고가 없다는 안내는 위 건수 줄에 이미 있습니다. 여기서 또 적지 않습니다.
          !data && <div className="empty">불러오는 중입니다.</div>
        )}
      </div>

      {data && <Pager page={data.page} pages={data.pages} onGo={goPage} />}
    </section>
  );
}
