/* 전체 사업 현황 — 프로토타입 renderHome() 을 그대로 옮겼습니다. */
import { useState } from "react";
import Calendar, { calData } from "../components/Calendar";
import { clamp, dots, fmtMoney, todayISO } from "../lib/format";
import type { ProjectDetail, ProjectSummary } from "../lib/types";

interface Props {
  projects: ProjectSummary[];
  // 달력에 할 일 기한을 함께 표시하려면 사업별 할 일이 필요합니다
  details: Record<string, ProjectDetail>;
  onGo: (projId: string) => void;
  onZoom: (scope: "home", ym: Date, picked: string) => void;
}

const ic = (children: React.ReactNode) => (
  <svg className="ic" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{children}</svg>
);

export default function Home({ projects, details, onGo, onZoom }: Props) {
  const [ym, setYm] = useState(() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1); });
  const [picked, setPicked] = useState("");

  /* 종료일이 지난 사업은 따로 뺍니다. 끝난 사업이 쌓이면 지금 챙길 사업이
     묻히고, 합계도 '여태 한 사업 전부' 가 되어 지금 규모를 알 수 없습니다.
     지운 것이 아니라 접어 둔 것이라 표 아래에서 펼쳐 볼 수 있습니다. */
  const 진행중 = projects.filter((p) => p.dday.cls !== "closed");
  const 종료됨 = projects.filter((p) => p.dday.cls === "closed");
  const [종료펼침, set종료펼침] = useState(false);

  const totalBudget = 진행중.reduce((s, p) => s + (p.budget || 0), 0);
  const totalSpent = 진행중.reduce((s, p) => s + p.spent, 0);
  const attention = 진행중.filter((p) => p.status.key !== "g").length;
  const execRate = totalBudget > 0 ? (totalSpent / totalBudget) * 100 : 0;

  /* 달력에는 종료된 사업도 그대로 둡니다. 지난 일정을 되짚어 볼 때
     사업 기간 띠가 없으면 무슨 일이었는지 알 수 없습니다. */
  const withTodos = projects.map((p) => ({ ...p, todos: details[p.id]?.todos ?? [] }));
  const { events, runs } = calData(withTodos, projects);

  const 사업줄 = (p: (typeof projects)[number]) => (
              <tr key={p.id}>
      <td>
        <span className={"pill " + p.status.key}
              style={{ minWidth: 86, padding: "4px 10px", fontSize: "13.8px" }}>
          {p.status.label}
        </span>
      </td>
      <td>
        <button type="button" className="home-name" onClick={() => onGo(p.id)}>{p.name}</button>
        <div className="home-sub">{p.agency || "발주처 미입력"} · {p.cycle} 보고</div>
      </td>
      <td>
        <span className="cellnum">{p.actual}%</span>{" "}
        <span className="cellsub">/ 계획 {p.planned}%</span>
        <div className="minibar">
          <i style={{ width: `${p.actual}%` }} />
          <span className="pin" style={{ left: `calc(${p.planned}% - 1px)` }} />
        </div>
      </td>
      <td className="num">
        <span className="cellnum"
              style={{ color: p.diff >= 0 ? "var(--good-ink)" : "var(--crit-ink)" }}>
          {p.diff >= 0 ? "+" : "−"}{Math.abs(p.diff)}%p
        </span>
      </td>
      {/* 금액을 원 단위로 적으니 칸을 넘겼습니다. 집행률만 두고,
          실제 금액은 대시보드의 비목별 막대와 같은 방식으로
          막대에 마우스를 올렸을 때 위에 띄웁니다. */}
      <td>
        <span className="cellnum">{p.rate.toFixed(1)}%</span>{" "}
        <span className="cellsub">집행</span>
        <div className="bar-hover">
          <div className="minibar"><i style={{ width: `${clamp(p.rate, 0, 100)}%` }} /></div>
          <span className="tip">{fmtMoney(p.spent)} / {fmtMoney(p.budget)}</span>
        </div>
      </td>
      <td className="cellsub">
        {dots(p.start)}<br />~ {dots(p.end)}
        <div className={"dday " + p.dday.cls} style={{ marginTop: 2 }}>{p.dday.txt}</div>
      </td>
      <td>{p.latestIssue || <span style={{ color: "var(--muted)" }}>없음</span>}</td>
    </tr>
  );

  function moveCal(step: number) {
    if (step === 0) {
      const t = new Date();
      setYm(new Date(t.getFullYear(), t.getMonth(), 1));
      // toISOString() 은 UTC 라 한국시간 자정~오전 9시 사이에 '어제'가 됩니다
      setPicked(todayISO());
    } else {
      setYm(new Date(ym.getFullYear(), ym.getMonth() + step, 1));
      setPicked("");
    }
  }

  return (
    <section className="view on">
      <div className="page-title">전체 사업 현황</div>

      <div className="home-tiles" id="homeTiles">
        <div className="tile">
          {ic(<><path d="M3 7h18v13H3z"/><path d="M8 7V5a2 2 0 012-2h4a2 2 0 012 2v2"/></>)}
          <div className="k">진행 중 사업</div>
          <div className="v">{projects.length}건</div>
        </div>
        <div className="tile">
          {ic(<><path d="M3 6h18v12H3z"/><circle cx="12" cy="12" r="2.5"/><path d="M6 12h.01M18 12h.01"/></>)}
          <div className="k">총 사업비</div>
          <div className="v">{fmtMoney(totalBudget)}</div>
        </div>
        <div className="tile">
          {ic(<><path d="M3 17l6-6 4 4 7-7"/><path d="M14 8h6v6"/></>)}
          <div className="k">총 집행액</div>
          <div className="v">{fmtMoney(totalSpent)} <span className="unit">집행률 {execRate.toFixed(1)}%</span></div>
          <div className="tile-meter"><i style={{ width: `${clamp(execRate, 0, 100)}%` }} /></div>
        </div>
        <div className={"tile" + (attention ? " alert" : "")}>
          {ic(<><path d="M10.3 3.9L2.6 17a2 2 0 001.7 3h15.4a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z"/><path d="M12 9v4M12 17h.01"/></>)}
          <div className="k">점검·조치 필요</div>
          <div className="v">{attention}건</div>
        </div>
      </div>

      {/* 달력(1/3)과 사업별 현황(2/3)을 한 줄에 둡니다.
          화면이 좁으면 overrides.css 가 위아래로 다시 쌓습니다. */}
      <div className="home-split">

      {/* 전체 일정 달력. 사업 진행 기간은 형광펜처럼 칠해집니다. */}
      <div className="card cal-card" id="calCard-home">
        <h2>내 사업 일정
          <button type="button" className="cal-zoom" id="calZoomBtn-home"
                  title="크게 보기" aria-label="달력 크게 보기"
                  onClick={() => onZoom("home", ym, picked)}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <polyline points="15 3 21 3 21 9" />
              <polyline points="9 21 3 21 3 15" />
              <line x1="21" y1="3" x2="14" y2="10" />
              <line x1="3" y1="21" x2="10" y2="14" />
            </svg>
          </button>
        </h2>
        <div className="cal-head">
          <button type="button" className="cal-nav" onClick={() => moveCal(-1)} aria-label="이전 달">‹</button>
          <div className="cal-title" id="calTitle-home">{ym.getFullYear()}년 {ym.getMonth() + 1}월</div>
          <button type="button" className="cal-nav" onClick={() => moveCal(1)} aria-label="다음 달">›</button>
          <button type="button" className="mini-btn cal-today" onClick={() => moveCal(0)}>오늘</button>
        </div>
        <div className="cal-dow" aria-hidden="true">
          <span>일</span><span>월</span><span>화</span><span>수</span><span>목</span><span>금</span><span>토</span>
        </div>
        <Calendar
          ym={ym} picked={picked} big={false} events={events} runs={runs}
          showRunLegend onPick={(iso) => setPicked(picked === iso ? "" : iso)}
          onGo={onGo} idSuffix="home"
        />
      </div>

      <div className="card home-list">
        <h2>사업별 현황 <span className="hint">사업명을 누르면 상세 대시보드로 이동합니다</span></h2>
        <div className="tbl-wrap"><table className="tbl">
          <thead><tr>
            <th style={{ width: 92 }}>상태</th>
            <th>사업명</th>
            <th style={{ width: 155 }}>진행률</th>
            <th className="num" style={{ width: 92 }}>계획 대비</th>
            <th style={{ width: 165 }}>예산 집행</th>
            <th style={{ width: 150 }}>사업 기간</th>
            <th style={{ width: 185 }}>최근 확인사항</th>
          </tr></thead>
          <tbody id="homeBody">
            {진행중.length ? 진행중.map(사업줄) : (
              <tr><td colSpan={7}><div className="empty">
                {종료됨.length ? "진행 중인 사업이 없습니다." : "아직 등록된 사업이 없습니다. 왼쪽 메뉴의 [신규 사업 등록]에서 시작하세요."}
              </div></td></tr>
            )}
            {종료됨.length > 0 && (
              <tr className="fold-row">
                <td colSpan={7}>
                  <button type="button" className="nav-fold" aria-expanded={종료펼침}
                          onClick={() => set종료펼침(!종료펼침)}>
                    <span className="caret" aria-hidden="true">{종료펼침 ? "▾" : "▸"}</span>
                    종료된 사업 {종료됨.length}
                  </button>
                </td>
              </tr>
            )}
            {종료펼침 && 종료됨.map(사업줄)}
          </tbody>
        </table></div>
      </div>

      </div>{/* .home-split */}
    </section>
  );
}
