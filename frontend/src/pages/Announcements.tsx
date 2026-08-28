/* 사업 현황 (공고) — 프로토타입 renderAnn() 을 옮겼습니다.

   프로토타입과 달라지는 점은 '걸러내기와 정렬을 서버에서 한다'는 것뿐입니다.
   판단 기준(접수예정/접수중/마감, 금액 구간, 키워드를 제목·사업명에만 맞춤,
   마감 임박순 묶음 순서)은 그대로입니다.

   NTIS 통합공고를 붙이면 전 부처라 수천 건이 됩니다. 그만큼을 브라우저로
   내려보낼 수 없어 한 쪽씩(기본 40건) 받습니다. */
import { useCallback, useEffect, useRef, useState } from "react";
import Pager from "../components/Pager";
import { annApi, type Ann, type AnnPage, type CollectorStatus } from "../lib/annApi";
import { describeCron } from "../lib/cron";
import { fmtEok } from "../lib/format";
import type { AppSettings } from "../lib/types";
import "../styles/pager.css";

const SIZE_KEY = "bizDash.v3.annPageSize";

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
  onModal: (msg: string, sub?: string, onOk?: () => void) => void;
  onEditAnn: (a: Ann | null) => void;
  // 공고 추가 폼의 '부처' 자동완성에 쓰라고 위로 올려 줍니다
  onFacets: (ministries: string[]) => void;
  reloadToken: number;          // 등록·수정·불러오기 뒤 목록을 다시 받게 하는 값
}

export default function Announcements({
  settings, onSettings, onModal, onEditAnn, onFacets, reloadToken,
}: Props) {
  const f = settings.ann_filter;
  const [data, setData] = useState<AnnPage | null>(null);
  const [collector, setCollector] = useState<CollectorStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const [tab, setTab] = useState("all");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("due");
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(() => {
    const v = Number(localStorage.getItem(SIZE_KEY));
    return [20, 40, 60].includes(v) ? v : 40;
  });
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
    });
  }

  const last = collector?.last;
  const 마지막수집 = last
    ? `${last.startedAt.slice(5, 16).replace("T", " ").replace("-", "/")} · ${last.totalSeen}건`
    : "아직 없음";
  const 잘림 = last?.detail?.sources?.some((s) => s.truncated);
  const 실패 = last?.detail?.sources?.filter((s) => s.error) ?? [];

  return (
    <section className="view on">
      <div className="page-title" id="annTop">사업 현황 — 대외 공고</div>

      {/* 수집이 조용히 멈춰 있는 걸 모르는 게 제일 위험합니다 */}
      <div className="collect-bar">
        <span className={"dot" + (last ? (실패.length || 잘림 ? " stale" : "") : " none")} />
        <span>마지막 수집 <b style={{ color: "var(--ink-2)" }}>{마지막수집}</b></span>
        {잘림 && <span style={{ color: "var(--warn-ink)" }}>· 일부 서버가 응답을 끊었습니다</span>}
        {실패.length > 0 && (
          <span style={{ color: "var(--crit-ink)" }}>· {실패.map((s) => s.name).join(", ")} 실패</span>
        )}
        {collector?.enabled && (
          <span style={{ color: "var(--muted)" }}>· 자동 수집 {describeCron(collector.cron)}</span>
        )}
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
          <option value="due">마감 임박순</option>
          <option value="posted">공고일 최신순</option>
          <option value="amount">공고금액 큰순</option>
          <option value="score">관련도순</option>
        </select>
      </div>

      <div className="ann-count" id="annCount">
        {data && (data.total
          ? <span>전체 <b>{data.total.toLocaleString()}건</b> 중 {data.from.toLocaleString()} – {data.to.toLocaleString()}번째</span>
          : <span>조건에 맞는 공고가 없습니다</span>)}
        <span className="size">
          <label htmlFor="annSize">쪽당</label>
          <select id="annSize" value={size}
                  onChange={(e) => { const v = Number(e.target.value); setSize(v); localStorage.setItem(SIZE_KEY, String(v)); }}>
            <option value={20}>20개</option>
            <option value={40}>40개</option>
            <option value={60}>60개</option>
          </select>
        </span>
      </div>

      {err && <div className="form-err on">{err}</div>}

      <div className="ann-grid" id="annGrid">
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
                <button type="button" className="mini-btn" onClick={() => onEditAnn(a)}>수정</button>
                <button type="button" className="mini-btn danger" onClick={() => removeAnn(a)}>삭제</button>
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
