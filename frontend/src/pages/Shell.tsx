/* 로그인 뒤 전체 화면 — 프로토타입의 go() / 화면 전환을 옮겼습니다. */
import { useCallback, useEffect, useState } from "react";
import Calendar, { calData } from "../components/Calendar";
import Modal, { type ModalState } from "../components/Modal";
import { todayISO } from "../lib/format";
import Sidebar, { type View } from "../components/Sidebar";
import { api } from "../lib/api";
import type { AppSettings, ProjectDetail, ProjectSummary } from "../lib/types";
import Dashboard from "./Dashboard";
import Home from "./Home";
import Register, { type Prefill } from "./Register";
import Announcements from "./Announcements";
import AnnForm from "../components/AnnForm";
import type { Ann } from "../lib/annApi";



interface FullCal {
  scope: "home" | "dash";
  ym: Date;
  picked: string;
}

export default function Shell() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [details, setDetails] = useState<Record<string, ProjectDetail>>({});
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [view, setView] = useState<View>("home");
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [full, setFull] = useState<FullCal | null>(null);
  const [error, setError] = useState("");
  const [modal, setModal] = useState<ModalState | null>(null);
  // 사업 정보 수정 모드로 들어왔는지 (null 이면 신규 등록)
  const [editingProjectId, setEditingProjectId] = useState<string | null>(null);
  const [manualDraft, setManualDraft] = useState<string | null>(null);
  // 공고 화면 — 등록·수정 팝업과 불러오기 팝업, 그리고 목록 새로고침 신호
  const [annForm, setAnnForm] = useState<{ ann: Ann | null } | null>(null);
  const [annReload, setAnnReload] = useState(0);
  const [annMinistries, setAnnMinistries] = useState<string[]>([]);
  // 공고에서 [사업 등록] 을 눌렀을 때 등록 화면에 옮겨 넣을 값
  const [prefill, setPrefill] = useState<Prefill | null>(null);

  // 첫 화면에 필요한 것을 한 번에 받아 둡니다.
  // 달력에 할 일 기한을 표시하려면 사업별 상세가 필요합니다.
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [list, cfg] = await Promise.all([api.projects(), api.settings()]);
        if (!alive) return;
        setProjects(list);
        setSettings(cfg);
        setCurrentId((id) => id ?? (list[0]?.id ?? null));
        const loaded = await Promise.all(list.map((p) => api.project(p.id)));
        if (!alive) return;
        setDetails(Object.fromEntries(loaded.map((d) => [d.id, d])));
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : "불러오지 못했습니다.");
      }
    })();
    return () => { alive = false; };
  }, []);

  /* 화면을 옮기면 달력은 이번 달로 되돌립니다. 다른 화면을 다녀왔는데 지난달이
     그대로 떠 있으면 지금 상황을 보고 있다고 착각하기 쉽습니다. */
  const go = useCallback((next: View, projId?: string) => {
    setView(next);
    if (projId) setCurrentId(projId);
    setFull(null);
    // 메뉴의 '신규 사업 등록'을 누르면 항상 신규 모드로 시작합니다
    if (next !== "register") setEditingProjectId(null);
    window.scrollTo({ top: 0 });
  }, []);

  // 목록과 상세를 함께 갱신합니다 (왼쪽 사업 목록의 상태 점도 같이 바뀝니다)
  const applyProject = useCallback((next: ProjectDetail) => {
    setDetails((d) => ({ ...d, [next.id]: next }));
    setProjects((list) => list.some((x) => x.id === next.id)
      ? list.map((x) => (x.id === next.id ? { ...x, ...next } : x))
      : [...list, next]);
  }, []);

  const openModal = useCallback((msg: string, sub?: string, onOk?: () => void, danger?: boolean) => {
    setModal({ msg, sub, onOk, danger });
  }, []);

  const detail = currentId ? details[currentId] : undefined;

  // '크게 보기' 팝업에 넣을 데이터 — 열어 준 달력의 것을 그대로 씁니다
  const fullData = (() => {
    if (!full) return null;
    if (full.scope === "dash" && detail) {
      return {
        title: `${detail.name} 일정`,
        ...calData([{ ...detail, todos: detail.todos }], projects),
        showRunLegend: false,
      };
    }
    const withTodos = projects.map((p) => ({ ...p, todos: details[p.id]?.todos ?? [] }));
    return { title: "내 사업 일정", ...calData(withTodos, projects), showRunLegend: true };
  })();

  return (
    <div className="app">
      <Sidebar
        projects={projects}
        view={view}
        currentId={currentId}
        manualUrl={settings?.manual_url.url ?? ""}
        onGo={(v, id) => { if (v === "register") setPrefill(null); go(v, id); }}
        onEditManual={() => setManualDraft(settings?.manual_url.url ?? "")}
      />

      <main className="main">

        {error && <div className="form-err on" style={{ marginBottom: 16 }}>{error}</div>}

        {view === "home" && (
          <Home
            projects={projects}
            details={details}
            onGo={(id) => go("dash", id)}
            onZoom={(scope, ym, picked) => setFull({ scope, ym, picked })}
          />
        )}

        {view === "dash" && (detail ? (
          /* key 에 사업 id 를 주어, 사업을 바꾸면 화면이 새로 그려지게 합니다.

             이게 없으면 다른 사업으로 옮겨도 열어 둔 입력창과 '수정 중인 회차'가
             그대로 남습니다. 실제로 주간 사업의 회차 키(W2026-08-17)가 월간 사업
             화면에 남아 있었습니다.

             프로토타입도 go() 에서 화면을 옮길 때마다 입력창을 닫고 수정 상태를
             지웁니다(저장하지 않은 입력은 남기지 않습니다). 달력이 이번 달로
             돌아가는 것도 같은 이유입니다. */
          <Dashboard
            key={detail.id}
            p={detail}
            allProjects={projects}
            onGo={(id) => go("dash", id)}
            onZoom={(scope, ym, picked) => setFull({ scope, ym, picked })}
            onProjectChange={applyProject}
            onModal={openModal}
            onEdit={() => { setEditingProjectId(detail.id); go("register"); }}
          />
        ) : (
          <section className="view on"><div className="empty">사업을 불러오는 중입니다.</div></section>
        ))}

        {view === "register" && (
          <Register
            editing={editingProjectId ? details[editingProjectId] ?? null : null}
            prefill={prefill}
            onSaved={(saved, msg, sub) => {
              applyProject(saved);
              setEditingProjectId(null);
              setPrefill(null);
              go("dash", saved.id);
              openModal(msg, sub);
            }}
            onDeleted={(name) => {
              const gone = editingProjectId;
              setEditingProjectId(null);
              setDetails((d) => { const n = { ...d }; if (gone) delete n[gone]; return n; });
              setProjects((list) => {
                const next = list.filter((x) => x.id !== gone);
                setCurrentId(next[0]?.id ?? null);
                return next;
              });
              go("home");
              openModal("삭제되었습니다", name);
            }}
            onCancel={() => {
              const id = editingProjectId;
              setEditingProjectId(null);
              setPrefill(null);
              if (id) go("dash", id); else go("home");
            }}
            onModal={openModal}
          />
        )}

        {view === "ann" && settings && (
          <Announcements
            settings={settings}
            onSettings={setSettings}
            onModal={openModal}
            onEditAnn={(a) => setAnnForm({ ann: a })}
            onToProject={(a) => {
              /* 공고를 '내 사업'으로 옮깁니다.
                 공고 목록에는 사업 기간·추진과제가 없으므로 채울 수 있는 것만
                 채우고, 나머지는 사람이 적도록 안내합니다. */
              setEditingProjectId(null);
              setPrefill({
                name: a.title,
                agency: [a.ministry, a.agency].filter(Boolean).join(" · "),
                budget: a.amount
                  ? (a.amount / 1e8).toLocaleString("ko-KR", { maximumFractionDigits: 2 })
                  : "",
              });
              go("register");
              openModal("공고 정보를 옮겼습니다", "사업 기간과 추진과제를 채워 등록하세요.");
            }}
            onFacets={setAnnMinistries}
            reloadToken={annReload}
          />
        )}

      </main>


      {/* 사업 매뉴얼 문서 주소 — 노션 등 외부 문서로 바로 가는 메뉴에 씁니다 */}
      {manualDraft !== null && (
        <div className="scrim on" role="dialog" aria-modal="true">
          <form className="modal form" style={{ maxWidth: 520 }}
                onSubmit={async (e) => {
                  e.preventDefault();
                  try {
                    const r = await api.setManualUrl(manualDraft);
                    setSettings((s) => (s ? { ...s, manual_url: { url: r.url } } : s));
                    setManualDraft(null);
                  } catch (ex) {
                    openModal(ex instanceof Error ? ex.message : "저장하지 못했습니다.");
                  }
                }}>
            <h3>사업 매뉴얼 주소</h3>
            <p style={{ fontSize: "14.4px", color: "var(--ink-2)", marginBottom: 12 }}>
              노션 등 사업 매뉴얼 문서 주소를 넣어 두면 왼쪽 메뉴에서 바로 열 수 있습니다.
            </p>
            <div className="f">
              <input autoFocus value={manualDraft} spellCheck={false}
                     placeholder="https://www.notion.so/..."
                     onChange={(e) => setManualDraft(e.target.value)} />
            </div>
            <div className="acts" style={{ marginTop: 16 }}>
              <button type="button" className="no" onClick={() => setManualDraft(null)}>취소</button>
              <button type="submit" className="ok">저장</button>
            </div>
          </form>
        </div>
      )}

      {annForm && (
        <AnnForm
          ann={annForm.ann}
          ministries={annMinistries}
          onDone={() => { setAnnForm(null); setAnnReload((n) => n + 1); }}
          onClose={() => setAnnForm(null)}
        />
      )}


      <Modal state={modal} onClose={() => setModal(null)} />

      {/* 달력 크게 보기 */}
      {full && fullData && (
        <div className="scrim on" id="calScrim" role="dialog" aria-modal="true">
          <div className="modal cal-full cal-card big">
            <div className="cal-full-head">
              <h3 id="calFullName">{fullData.title}</h3>
              <button type="button" className="cal-close" onClick={() => setFull(null)}
                      aria-label="닫기" autoFocus>×</button>
            </div>
            <div className="cal-head">
              <button type="button" className="cal-nav" aria-label="이전 달"
                      onClick={() => setFull({ ...full, ym: new Date(full.ym.getFullYear(), full.ym.getMonth() - 1, 1), picked: "" })}>‹</button>
              <div className="cal-title" id="calTitle-full">
                {full.ym.getFullYear()}년 {full.ym.getMonth() + 1}월
              </div>
              <button type="button" className="cal-nav" aria-label="다음 달"
                      onClick={() => setFull({ ...full, ym: new Date(full.ym.getFullYear(), full.ym.getMonth() + 1, 1), picked: "" })}>›</button>
              <button type="button" className="mini-btn cal-today"
                      onClick={() => { const t = new Date();
                        setFull({ ...full, ym: new Date(t.getFullYear(), t.getMonth(), 1),
                                  // toISOString 은 UTC 라 새벽에 '어제'가 됩니다
                                  picked: todayISO() }); }}>오늘</button>
            </div>
            <div className="cal-dow" aria-hidden="true">
              <span>일</span><span>월</span><span>화</span><span>수</span><span>목</span><span>금</span><span>토</span>
            </div>
            <Calendar
              ym={full.ym} picked={full.picked} big events={fullData.events} runs={fullData.runs}
              showRunLegend={fullData.showRunLegend}
              onPick={(iso) => setFull({ ...full, picked: full.picked === iso ? "" : iso })}
              onGo={(id) => go("dash", id)}
              idSuffix="full"
            />
          </div>
        </div>
      )}
    </div>
  );
}
