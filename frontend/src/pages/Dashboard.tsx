/* 사업 대시보드 — 프로토타입 renderDash() / renderHistory() / renderTodos() 를 옮겼습니다.
   4단계에서 입력 패널을 붙일 자리는 비워 두었습니다 (지금은 조회 전용). */
import { useState } from "react";
import Calendar, { calData } from "../components/Calendar";
import InputPanel from "../components/InputPanel";
import { api } from "../lib/api";
import { clamp, daysBetween, dots, fmtMoney, fmtWon, todayISO } from "../lib/format";
import type { ProjectDetail, ProjectSummary } from "../lib/types";

interface Props {
  p: ProjectDetail;
  allProjects: ProjectSummary[];
  onGo: (projId: string) => void;
  onZoom: (scope: "dash", ym: Date, picked: string) => void;
  onProjectChange: (p: ProjectDetail) => void;
  onModal: (msg: string, sub?: string, onOk?: () => void, danger?: boolean) => void;
  onEdit: () => void;
}

const 폴더아이콘 = (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
  </svg>
);

export default function Dashboard({
  p, allProjects, onGo, onZoom, onProjectChange, onModal, onEdit,
}: Props) {
  const [ym, setYm] = useState(() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1); });
  const [picked, setPicked] = useState("");
  const [inputOpen, setInputOpen] = useState(false);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [todoText, setTodoText] = useState("");

  async function run(fn: () => Promise<ProjectDetail>, msg?: string) {
    try {
      onProjectChange(await fn());
      if (msg) onModal(msg);
    } catch (e) {
      onModal(e instanceof Error ? e.message : "처리하지 못했습니다.");
    }
  }

  function editEntry(pkey: string) {
    setEditingKey(pkey);
    setInputOpen(true);
    setTimeout(() => document.getElementById("weeklyForm")
      ?.scrollIntoView({ block: "start", behavior: "smooth" }), 50);
  }

  function deleteEntry(pkey: string) {
    const e = p.entries.find((x) => x.periodKey === pkey);
    if (!e) return;
    onModal("이 회차 입력을 삭제할까요?",
      e.periodLabel + " · 집행액과 성과 실적이 함께 제외됩니다.",
      () => void run(async () => {
        const r = await api.deleteEntry(p.id, pkey);
        if (editingKey === pkey) setEditingKey(null);
        return r.project;
      }, "삭제되었습니다"), true);
  }

  /* 목록 맨 아래 줄에서 바로 부릅니다(폼이 없습니다).
     기한은 달력에서 고른 날짜를 씁니다. 적고 나면 글자만 비우고 고른 날짜는
     그대로 두어, 같은 날 할 일을 여러 건 이어서 적을 수 있게 합니다. */
  function addTodo() {
    if (!todoText.trim()) return;
    void run(async () => {
      const r = await api.addTodo(p.id, todoText, picked);
      setTodoText("");
      return r;
    });
  }

  const { events, runs } = calData([{ ...p, todos: p.todos }], allProjects);

  function moveCal(step: number) {
    if (step === 0) {
      const t = new Date();
      setYm(new Date(t.getFullYear(), t.getMonth(), 1));
      setPicked(todayISO());
    } else {
      setYm(new Date(ym.getFullYear(), ym.getMonth() + step, 1));
      setPicked("");
    }
  }

  /* 진행률 숫자와 게이지 색 — 오직 '계획 대비'만 봅니다.
     상태 배지는 미해결 확인사항이 있으면 노랑이 되지만, 이 숫자는 진척만 나타내야
     하므로 확인사항은 반영하지 않습니다. (서버가 progressColor 로 내려줍니다.) */
  const 진척색 = p.progressColor;

  const 확인사항 = p.entries.filter((e) => e.issue.trim()).slice().reverse();
  const 미해결 = 확인사항.filter((e) => !e.issueDone);
  const 해결됨 = 확인사항.filter((e) => e.issueDone).slice(0, 3);

  const 배정있음 = p.catRows.some((c) => c.allocated > 0);
  const 최대 = Math.max(1, ...p.catRows.map((c) => Math.max(c.allocated, c.used)));

  const 남은할일 = p.todos.filter((t) => !t.done).length;
  const 정렬된할일 = p.todos.slice().sort((a, b) => {
    if (a.done !== b.done) return a.done ? 1 : -1;
    return (a.due || "9999") < (b.due || "9999") ? -1 : 1;
  });

  const 웹주소 = /^https?:\/\//i.test(p.folderUrl || "");

  const 확인사항카드 = (e: typeof p.entries[number]) => (
    <div key={e.periodKey} className={"issue " + (e.issueDone ? "done" : "")}>
      <div className="ihead">
        <div className="t">{e.issue}</div>
        <button type="button" className="mini-btn"
                onClick={() => void run(async () =>
                  (await api.toggleIssue(p.id, e.periodKey)).project)}>
          {e.issueDone ? "되돌리기" : "해결"}
        </button>
      </div>
      <div className="a"><b>조치</b> {e.plan || "미입력"}</div>
      <div className="d">{e.periodFull}{e.issueDone ? " · 해결됨" : ""}</div>
    </div>
  );

  return (
    <section className="view on">
      <div className="proj-head">
        <div>
          <h1 id="phName">{p.name}</h1>
          <div className="meta" id="phMeta">
            <span>{p.agency || "발주처 미입력"}</span>
            <span>{dots(p.start)} ~ {dots(p.end)} <b style={{ color: "var(--ink-2)" }}>{p.dday.txt}</b></span>
            <span>총 사업비 {fmtMoney(p.budget)}</span>
            <span>{p.cycle} 보고</span>
          </div>
        </div>
        <div className="right">
          <span id="phPill" className={"pill " + p.status.key}><span id="phPillTxt">{p.status.label}</span></span>
          <button type="button" className="btn-ghost" style={{ padding: "7px 12px" }}
                  onClick={onEdit}>사업 정보 수정</button>
          <button type="button" className={"btn-toggle" + (inputOpen ? " on" : "")} id="inputToggle"
                  aria-pressed={inputOpen}
                  onClick={() => { setInputOpen(!inputOpen); if (inputOpen) setEditingKey(null); }}>
            <span className="sw" aria-hidden="true" /><span id="toggleLbl">{p.cycleWord} 입력</span>
          </button>
        </div>
      </div>

      <div className={"dash-wrap" + (inputOpen ? " open" : "")} id="dashWrap">
        <div className="dash-grid">

          <div className="card span2">
            <h2>성과지표 · 목표 대비 달성률</h2>
            <div className="kpi-grid" id="kpiGrid">
              {p.kpis.map((k) => {
                const raw = k.target > 0 ? (k.value / k.target) * 100 : 0;
                return (
                  <div key={k.name} className="kpi">
                    <div className="nm"><span className="t" title={k.name}>{k.name}</span></div>
                    <div className="val">{k.value.toLocaleString()}<small> / {k.target.toLocaleString()}{k.unit}</small></div>
                    <div className="track"><div className="fill" style={{ width: `${clamp(raw, 0, 100)}%` }} /></div>
                    <div className="pct">{Math.round(raw)}%</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 이 사업의 일정 */}
          <div className="card cal-card" id="calCard-dash">
            <h2>사업 일정
              <button type="button" className="cal-zoom" id="calZoomBtn-dash"
                      title="크게 보기" aria-label="달력 크게 보기"
                      onClick={() => onZoom("dash", ym, picked)}>
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
              <div className="cal-title" id="calTitle-dash">{ym.getFullYear()}년 {ym.getMonth() + 1}월</div>
              <button type="button" className="cal-nav" onClick={() => moveCal(1)} aria-label="다음 달">›</button>
              <button type="button" className="mini-btn cal-today" onClick={() => moveCal(0)}>오늘</button>
            </div>
            <div className="cal-dow" aria-hidden="true">
              <span>일</span><span>월</span><span>화</span><span>수</span><span>목</span><span>금</span><span>토</span>
            </div>
            <Calendar
              ym={ym} picked={picked} big={false} events={events} runs={runs}
              showRunLegend={false}
              onPick={(iso) => {
                const 다음 = picked === iso ? "" : iso;
                // 고른 날짜가 곧 새 할 일의 기한입니다(아래 입력줄에서 씁니다).
                setPicked(다음);
              }}
              onGo={onGo} idSuffix="dash" pickAnyDay
            />
            {/* 할 일 — 달력과 한 카드에 둡니다.
                입력칸을 따로 두지 않고 목록 맨 아래 줄에서 바로 적습니다.
                기한은 달력에서 고른 날짜를 씁니다(안 고르면 기한 없음). */}
            <div className="cal-todo">
              <h3>할 일 <span className="hint">
                {p.todos.length ? `남은 일 ${남은할일}건 / 전체 ${p.todos.length}건` : ""}
              </span></h3>
              <div id="todoList">
                {정렬된할일.map((t) => {
                  const 남은일 = t.due ? daysBetween(todayISO(), t.due) : null;
                  const 급함 = !t.done && 남은일 !== null && 남은일 <= 3;
                  return (
                    <div key={t.id} className={"todo " + (t.done ? "done" : "")}>
                      <input type="checkbox" checked={t.done} aria-label="완료 표시"
                             onChange={() => void run(() => api.toggleTodo(p.id, t.id))} />
                      <div style={{ flex: 1 }}>
                        <div className="tx">{t.text}</div>
                        {t.due && (
                          <div className={"due" + (급함 ? " soon" : "")}>
                            {dots(t.due)}
                            {!t.done && (남은일! < 0 ? ` · ${Math.abs(남은일!)}일 지남`
                              : 남은일 === 0 ? " · 오늘까지" : ` · ${남은일}일 남음`)}
                          </div>
                        )}
                      </div>
                      <button type="button" className="rm" aria-label="할 일 삭제"
                              onClick={() => void run(() => api.removeTodo(p.id, t.id))}>×</button>
                    </div>
                  );
                })}

                {/* 맨 아래 줄에서 바로 적습니다. Enter 로 들어가고 입력칸은 열린 채로
                    있어 여러 건을 이어서 적을 수 있습니다. */}
                <div className="todo todo-new">
                  <span className="plus" aria-hidden="true">+</span>
                  <input
                    className="todo-new-input"
                    aria-label="할 일 추가"
                    placeholder={picked ? `${dots(picked)} 기한으로 추가` : "할 일을 적고 Enter"}
                    value={todoText}
                    onChange={(e) => setTodoText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") { e.preventDefault(); addTodo(); }
                      if (e.key === "Escape") setTodoText("");
                    }}
                    onBlur={() => { if (todoText.trim()) addTodo(); }}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <h2>예산 집행</h2>
            <div className="money-line">
              <span className="big" id="bdSpent">{fmtMoney(p.spent)}</span>
              <span className="of" id="bdTotal">/ {fmtMoney(p.budget)}</span>
            </div>
            <div className="meter">
              <div className="track"><div className="fill" id="bdFill" style={{ width: `${clamp(p.rate, 0, 100)}%` }} /></div>
              <div className="lbls"><span>0</span><span id="bdMax">{fmtMoney(p.budget)}</span></div>
            </div>
            <div className="minirow">
              <div className="stat"><div className="k">기간 경과</div><div className="v" id="bdElapsed">{p.planned}%</div></div>
              <div className="stat"><div className="k">집행률</div><div className="v" id="bdRate">{p.rate.toFixed(1)}%</div></div>
              <div className="stat"><div className="k">잔액</div><div className="v" id="bdLeft">{fmtMoney(p.left)}</div></div>
            </div>

            {/* 비목별 줄 — 오른쪽 숫자는 '잔액'입니다.
                배정액을 넣은 비목은 (배정액 − 사용액), 안 넣은 비목은 잔액을 알 수 없으므로
                배정액을 넣으러 갈 수 있는 자리를 둡니다. */}
            <div className="cat-rows" id="bdCats">
              {p.catRows.length ? (
                <>
                  <div className="cat-head">
                    비목별 남은 금액{배정있음 ? "" : " · 배정액을 넣어야 계산됩니다"}
                  </div>
                  {p.catRows.map((c) => {
                    const 기준 = c.allocated > 0 ? c.allocated : 최대;
                    const 폭 = clamp(Math.round((c.used / 기준) * 100), 0, 100);
                    const 초과 = c.allocated > 0 && c.used > c.allocated;
                    const 잔액 = c.allocated - c.used;
                    const 툴팁 = c.allocated > 0
                      ? `사용 ${fmtWon(c.used)}원 / 배정 ${fmtWon(c.allocated)}원`
                      : `사용 ${fmtWon(c.used)}원 · 배정액 미입력`;
                    return (
                      <div key={c.name} className="cat-row">
                        <span className="nm" title={c.name}>{c.name}</span>
                        <span className={"bar" + (초과 ? " over" : "")} role="button" tabIndex={0}
                              onClick={(e) => e.currentTarget.classList.toggle("on")}
                              onKeyDown={(e) => {
                                if (e.key === "Enter" || e.key === " ") {
                                  e.preventDefault();
                                  e.currentTarget.classList.toggle("on");
                                }
                              }}>
                          <i style={{ width: `${폭}%` }} /><span className="tip">{툴팁}</span>
                        </span>
                        {c.allocated > 0 ? (
                          <span className="v" style={초과 ? { color: "var(--crit-ink)" } : undefined}>
                            {fmtMoney(잔액)}
                          </span>
                        ) : (
                          <button type="button" className="v none link" onClick={onEdit}
                                  title="배정액을 넣으면 남은 금액이 표시됩니다">배정액 입력</button>
                        )}
                      </div>
                    );
                  })}
                </>
              ) : <div className="empty">집행 내역 없음</div>}
            </div>
          </div>

          <div className="card span2">
            <div className="band">
              <div>
                <div className="cap">계획 대비 진행률</div>
                <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
                  <span className={"n " + 진척색} id="heroPct">{p.actual}</span><span className="u">%</span>
                </div>
              </div>
              <div className="stats">
                <div className="stat"><div className="k">완료 과제</div><div className="v" id="stTasks">{p.tasksDone} / {p.tasksTotal}</div></div>
                <div className="stat"><div className="k">계획 진척률</div><div className="v" id="stPlan">{p.planned}%</div></div>
                <div className="stat"><div className="k">계획 대비</div>
                  <div className={"v " + (p.diff >= 0 ? "up" : "dn")} id="stDiff">
                    {p.diff >= 0 ? "+" : "−"}{Math.abs(p.diff)}%p
                  </div>
                </div>
                <div className="stat"><div className="k">예산 집행률</div><div className="v" id="stExec">{p.rate.toFixed(1)}%</div></div>
              </div>
            </div>
            <div className="bandbar">
              <div className="tick-lbl" id="heroTickLbl" style={{ left: `${clamp(p.planned, 6, 94)}%` }}>계획 {p.planned}%</div>
              <div className="track">
                <div className={"fill " + 진척색} id="heroFill" style={{ width: `${p.actual}%` }} />
                <div className="tick" id="heroTick" style={{ left: `calc(${p.planned}% - 1.5px)` }} />
              </div>
              <div className="ends"><span>0%</span><span>100%</span></div>
            </div>
          </div>

          <div className="card span2">
            <h2>상태 · 확인사항</h2>
            <div id="issueList">
              {미해결.length ? 미해결.map(확인사항카드)
                : <div className="empty">미해결 확인사항 없음 — 특이사항 없습니다.</div>}
              {해결됨.length > 0 && (
                <>
                  <div className="issue-sep">
                    해결된 확인사항 {확인사항.length - 미해결.length}건 중 최근 {해결됨.length}건
                  </div>
                  {해결됨.map(확인사항카드)}
                </>
              )}
            </div>
          </div>

          {/* 이 사업의 진행 단계 */}
          <div className="card span2">
            <h2>진행 단계</h2>
            <div className="stages" id="stageGauge">
              {p.stages.map((nm, i) => (
                <div key={nm} className={"stage " + (i < p.stage ? "done" : i === p.stage ? "now" : "")}>
                  <div className="seg" /><div className="nm">{nm}</div>
                </div>
              ))}
            </div>
            <div className="stagelist" id="stageList">
              {p.stages.map((nm, i) => {
                const note = (p.stageNotes[i] || "").trim();
                return (
                  <div key={nm} className={"stagerow " + (i < p.stage ? "done" : i === p.stage ? "now" : "")}>
                    <span className="nm">{nm}</span>
                    <span className={"tx " + (note ? "" : "empty")}>{note || "—"}</span>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="card span2">
            <h2>입력 내역 <span className="hint" id="histHint">{p.cycleWord} 보고 · 총 {p.entries.length}건</span></h2>
            <div className="tbl-wrap"><table className="tbl">
              <thead><tr>
                <th style={{ width: 215 }}>회차</th>
                <th className="num" style={{ width: 135 }}>집행액 (원)</th>
                <th style={{ width: 135 }}>비목</th>
                <th>활동 요약</th>
                <th style={{ width: 140 }}>확인사항</th>
                <th style={{ width: 135 }} />
              </tr></thead>
              <tbody id="histBody">
                {p.entries.length ? p.entries.slice().reverse().map((e) => (
                  <tr key={e.periodKey}>
                    <td>{e.periodFull}</td>
                    <td className="num">{fmtWon(e.spendTotal)}</td>
                    <td title={e.spends.map((s) => `${s.cat} ${s.amt}`).join(", ")}>{e.catSummary}</td>
                    <td className="act">{e.act || "-"}</td>
                    <td>
                      {e.issue.trim() ? (
                        <>{e.issue}{e.issueDone && <span className="tag-done">해결</span>}</>
                      ) : <span style={{ color: "var(--muted)" }}>없음</span>}
                    </td>
                    <td><div className="rowbtns">
                      <button type="button" className="mini-btn"
                              onClick={() => editEntry(e.periodKey)}>수정</button>
                      <button type="button" className="mini-btn danger"
                              onClick={() => deleteEntry(e.periodKey)}>삭제</button>
                    </div></td>
                  </tr>
                )) : (
                  <tr><td colSpan={6}><div className="empty">입력된 회차가 없습니다.</div></td></tr>
                )}
              </tbody>
            </table></div>
          </div>

          {/* 사업 관련 자료가 있는 공유폴더로 바로 가는 줄 */}
          <div className="span2 dash-foot" id="dashFoot">
            {!p.folderUrl ? (
              <button type="button" className="folder-link off" onClick={onEdit}>
                {폴더아이콘} 공유폴더 주소 등록
              </button>
            ) : 웹주소 ? (
              <a className="folder-link" href={p.folderUrl} target="_blank" rel="noopener noreferrer">
                {폴더아이콘} 사업 공유폴더 열기
              </a>
            ) : (
              /* \\서버\폴더 같은 사내 경로는 브라우저가 웹페이지에서 열 수 없게 막아 두었으므로,
                 대신 주소를 복사해 탐색기 주소창에 붙여넣도록 안내합니다. */
              <button type="button" className="folder-link"
                      onClick={() => navigator.clipboard?.writeText(p.folderUrl)}
                      title={p.folderUrl}>
                {폴더아이콘} 공유폴더 경로 복사
              </button>
            )}
          </div>
        </div>

        <InputPanel
          p={p}
          editingKey={editingKey}
          onEditingKeyChange={setEditingKey}
          onSaved={(next, msg, sub) => {
            onProjectChange(next);
            if (msg) { setInputOpen(false); onModal(msg, sub); }
          }}
          onConflict={(msg, sub, onOverwrite) => onModal(msg, sub, onOverwrite)}
        />
      </div>
    </section>
  );
}
