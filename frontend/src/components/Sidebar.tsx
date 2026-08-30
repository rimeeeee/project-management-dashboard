/* 왼쪽 메뉴 — 프로토타입의 <aside class="sidebar"> 를 그대로 옮겼습니다.
   아이콘 SVG 도 원본 그대로입니다. */
import type { ProjectSummary } from "../lib/types";
import { currentTheme, themeButtonLabel, toggleTheme, type Theme } from "../lib/theme";
import { useState } from "react";

export type View = "home" | "dash" | "register" | "ann";

interface Props {
  projects: ProjectSummary[];
  view: View;
  currentId: string | null;
  manualUrl: string;
  onGo: (view: View, projId?: string) => void;
  onEditManual: () => void;
}

export default function Sidebar({
  projects, view, currentId, manualUrl, onGo, onEditManual,
}: Props) {
  const [theme, setTheme] = useState<Theme>(() => currentTheme());
  const has = !!manualUrl.trim();

  return (
    <aside className="sidebar">
      <div className="brand">
        <img className="brand-logo" src="/brand/logo.svg" alt="" />
        <div className="t">사업관리 대시보드</div>
      </div>

      <nav className="nav-group" aria-label="전체">
        <button
          className={"nav-btn" + (view === "home" ? " active" : "")}
          onClick={() => onGo("home")}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 10.5L12 3l9 7.5V20a1 1 0 01-1 1H4a1 1 0 01-1-1z"/></svg>
          <span className="nm">전체 사업 현황</span>
        </button>
      </nav>

      <nav className="nav-group" aria-label="내 사업">
        <div className="nav-label">내 사업</div>
        <div id="projNav">
          {projects.map((p) => (
            <button
              key={p.id}
              className={"nav-btn" + (view === "dash" && currentId === p.id ? " active" : "")}
              onClick={() => onGo("dash", p.id)}
              title={p.name}
            >
              <span className={"dot " + p.status.key} />
              <span className="nm">{p.name}</span>
            </button>
          ))}
        </div>
      </nav>

      <nav className="nav-group" aria-label="메뉴">
        <div className="nav-label">메뉴</div>
        <button
          className={"nav-btn" + (view === "register" ? " active" : "")}
          onClick={() => onGo("register")}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M12 5v14M5 12h14"/></svg>
          <span className="nm">신규 사업 등록</span>
        </button>
        <button
          className={"nav-btn" + (view === "ann" ? " active" : "")}
          onClick={() => onGo("ann")}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 11l18-7-7 18-2.5-7.5L3 11z"/></svg>
          <span className="nm">사업 현황 (공고)</span>
        </button>

        {/* 사업 매뉴얼 — 노션 등 외부 문서로 바로 이동합니다.
            주소를 <a href> 에 직접 넣습니다. window.open 으로 열면 이 화면이 들어 있는
            창을 떠나 버릴 수 있습니다. */}
        <div className="nav-row">
          <a
            className="nav-btn"
            id="manualBtn"
            href={has ? manualUrl : "#"}
            target={has ? "_blank" : undefined}
            rel="noopener noreferrer"
            onClick={(e) => { if (!has) { e.preventDefault(); onEditManual(); } }}
            title={has ? manualUrl : "주소를 넣으면 바로 열 수 있습니다"}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 5a2 2 0 012-2h9l5 5v11a2 2 0 01-2 2H6a2 2 0 01-2-2z"/><path d="M14 3v6h6M8 13h8M8 17h5"/></svg>
            <span className="nm">사업 매뉴얼</span>
            <span className="nav-ext" id="manualExt" aria-hidden="true" style={{ display: has ? "" : "none" }}>↗</span>
          </a>
          <button
            type="button"
            className="nav-edit"
            onClick={onEditManual}
            title="매뉴얼 주소 변경"
            aria-label="매뉴얼 주소 변경"
          >✎</button>
        </div>
      </nav>

      <div className="foot">
        <button className="btn-ghost" onClick={() => setTheme(toggleTheme())} id="themeBtn">
          {themeButtonLabel(theme)}
        </button>
      </div>
    </aside>
  );
}
