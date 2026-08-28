/* 전체 사업 현황 — 프로토타입 renderHome() 을 그대로 옮겼습니다. */
import { useState } from "react";
import Calendar, { calData } from "../components/Calendar";
import { clamp, dots, fmtEok, todayISO } from "../lib/format";
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

  const totalBudget = projects.reduce((s, p) => s + (p.budget || 0), 0);
  const totalSpent = projects.reduce((s, p) => s + p.spent, 0);
  const attention = projects.filter((p) => p.status.key !== "g").length;
  const execRate = totalBudget > 0 ? (totalSpent / totalBudget) * 100 : 0;

  const withTodos = projects.map((p) => ({ ...p, todos: details[p.id]?.todos ?? [] }));
  const { events, runs } = calData(withTodos, projects);

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
          <div className="v">{fmtEok(totalBudget)}</div>
        </div>
        <div className="tile">
          {ic(<><path d="M3 17l6-6 4 4 7-7"/><path d="M14 8h6v6"/></>)}
          <div className="k">총 집행액</div>
          <div className="v">{fmtEok(totalSpent)} <span className="unit">집행률 {execRate.toFixed(1)}%</span></div>
          <div className="tile-meter"><i style={{ width: `${clamp(execRate, 0, 100)}%` }} /></div>
        </div>
        <div className={"tile" + (attention ? " alert" : "")}>
          {ic(<><path d="M10.3 3.9L2.6 17a2 2 0 001.7 3h15.4a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z"/><path d="M12 9v4M12 17h.01"/></>)}
          <div className="k">점검·조치 필요</div>
          <div className="v">{attention}건</div>
        </div>
      </div>

      {/* 전체 일정 달력. 사업 진행 기간은 형광펜처럼 칠해집니다. */}
      <div className="card cal-card" id="calCard-home" style={{ marginTop: 16 }}>
        <h2>내 사업 일정
          <button type="button" className="mini-btn" id="calZoomBtn-home"
                  onClick={() => onZoom("home", ym, picked)}>크게 보기</button>
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

      <div className="card" style={{ marginTop: 16 }}>
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
            {projects.length ? projects.map((p) => (
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
                <td>
                  <span className="cellnum">{p.rate.toFixed(1)}%</span>{" "}
                  <span className="cellsub">{fmtEok(p.spent)} / {fmtEok(p.budget)}</span>
                  <div className="minibar"><i style={{ width: `${clamp(p.rate, 0, 100)}%` }} /></div>
                </td>
                <td className="cellsub">
                  {dots(p.start)}<br />~ {dots(p.end)}
                  <div className={"dday " + p.dday.cls} style={{ marginTop: 2 }}>{p.dday.txt}</div>
                </td>
                <td>{p.latestIssue || <span style={{ color: "var(--muted)" }}>없음</span>}</td>
              </tr>
            )) : (
              <tr><td colSpan={7}><div className="empty">아직 등록된 사업이 없습니다. 왼쪽 메뉴의 [신규 사업 등록]에서 시작하세요.</div></td></tr>
            )}
          </tbody>
        </table></div>
      </div>
    </section>
  );
}
