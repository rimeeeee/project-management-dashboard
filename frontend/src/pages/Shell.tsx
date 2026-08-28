/* 로그인 뒤 전체 화면 — 프로토타입의 go() / 화면 전환을 옮겼습니다. */
import { useCallback, useEffect, useState } from "react";
import Calendar, { calData } from "../components/Calendar";
import Modal, { type ModalState } from "../components/Modal";
import Sidebar, { type View } from "../components/Sidebar";
import { api } from "../lib/api";
import { getWhoami, setWhoami } from "../lib/whoami";
import type { AppSettings, ProjectDetail, ProjectSummary } from "../lib/types";
import Dashboard from "./Dashboard";
import Home from "./Home";

interface Props {
  usingDefaultPassword: boolean;
  onLogout: () => void;
}

interface FullCal {
  scope: "home" | "dash";
  ym: Date;
  picked: string;
}

export default function Shell({ usingDefaultPassword, onLogout }: Props) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [details, setDetails] = useState<Record<string, ProjectDetail>>({});
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [view, setView] = useState<View>("home");
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [full, setFull] = useState<FullCal | null>(null);
  const [error, setError] = useState("");
  const [modal, setModal] = useState<ModalState | null>(null);
  // 입력자 이름 — 계정을 두지 않기로 해서 직접 적습니다.
  // 한 번 적으면 이 브라우저에 기억됩니다.
  const [who, setWho] = useState(() => getWhoami());
  const [nameDraft, setNameDraft] = useState("");
  const [askName, setAskName] = useState(false);

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
    window.scrollTo({ top: 0 });
  }, []);

  const openModal = useCallback((msg: string, sub?: string, onOk?: () => void) => {
    setModal({ msg, sub, onOk });
  }, []);

  function saveName() {
    const v = nameDraft.trim();
    if (!v) return;
    setWhoami(v);
    setWho(v);
    setAskName(false);
  }

  async function logout() {
    try { await api.logout(); } finally { onLogout(); }
  }

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
        onGo={go}
        onEditManual={() => alert("매뉴얼 주소 변경은 5단계에서 붙입니다.")}
      />

      <main className="main">
        {usingDefaultPassword && (
          <div className="login-notice" style={{ marginBottom: 16 }}>
            지금은 개발용 기본 비밀번호로 동작하고 있습니다. 실제로 쓰기 전에{" "}
            <code>.venv/bin/python scripts/set_password.py</code> 로 비밀번호를 정해 주세요.
          </div>
        )}

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
          <Dashboard
            p={detail}
            allProjects={projects}
            who={who}
            onGo={(id) => go("dash", id)}
            onZoom={(scope, ym, picked) => setFull({ scope, ym, picked })}
            onProjectChange={(next) => {
              setDetails((d) => ({ ...d, [next.id]: next }));
              // 왼쪽 목록의 상태 점과 전체 현황도 함께 갱신합니다
              setProjects((list) => list.map((x) => (x.id === next.id ? { ...x, ...next } : x)));
            }}
            onModal={openModal}
            onNeedName={() => { setNameDraft(who); setAskName(true); }}
          />
        ) : (
          <section className="view on"><div className="empty">사업을 불러오는 중입니다.</div></section>
        ))}

        {(view === "register" || view === "ann") && (
          <section className="view on">
            <div className="page-title">{view === "register" ? "신규 사업 등록" : "사업 현황 — 대외 공고"}</div>
            <div className="card">
              <p style={{ color: "var(--ink-2)" }}>
                {view === "register"
                  ? "사업 등록·수정은 5단계에서 붙입니다."
                  : "공고 화면과 자동 수집은 6단계에서 붙입니다."}
              </p>
            </div>
          </section>
        )}

        <div style={{ marginTop: 24, paddingBottom: 24, display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: "14.4px", color: "var(--muted)" }}>
            입력자 {who ? <b style={{ color: "var(--ink-2)" }}>{who}</b> : "미지정"}
          </span>
          <button type="button" className="mini-btn"
                  onClick={() => { setNameDraft(who); setAskName(true); }}>이름 변경</button>
          <button type="button" className="btn-ghost" onClick={logout}>로그아웃</button>
        </div>
      </main>

      {/* 입력자 이름 — 저장할 때 누가 입력했는지 남기려면 필요합니다 */}
      {askName && (
        <div className="scrim on" role="dialog" aria-modal="true">
          <form className="modal form" style={{ maxWidth: 420 }}
                onSubmit={(e) => { e.preventDefault(); saveName(); }}>
            <h3>입력자 이름</h3>
            <p style={{ fontSize: "14.4px", color: "var(--ink-2)", marginBottom: 12 }}>
              입력한 내용에 누가 언제 넣었는지 함께 남깁니다.
              한 번 적으면 이 브라우저에 기억됩니다.
            </p>
            <div className="f">
              <input autoFocus value={nameDraft} onChange={(e) => setNameDraft(e.target.value)}
                     placeholder="예: 김담당" />
            </div>
            <div className="acts" style={{ marginTop: 16 }}>
              <button type="button" className="no" onClick={() => setAskName(false)}>취소</button>
              <button type="submit" className="ok">저장</button>
            </div>
          </form>
        </div>
      )}

      <Modal state={modal} onClose={() => setModal(null)} />

      {/* 달력 크게 보기 */}
      {full && fullData && (
        <div className="scrim on" id="calScrim" role="dialog" aria-modal="true">
          <div className="modal cal-modal">
            <div className="cal-modal-head">
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
                                  picked: new Date().toISOString().slice(0, 10) }); }}>오늘</button>
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
