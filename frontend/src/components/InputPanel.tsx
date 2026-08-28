/* 보고 회차 입력 패널 — 프로토타입 renderInputForm() / collectInput() / submitInput() 을 옮겼습니다.

   프로토타입과 달라지는 점은 저장 방식뿐입니다.
   프로토타입은 저장할 때 전체 데이터를 통째로 덮어썼습니다. 여기서는 그 회차
   한 줄만 서버에 보냅니다. 그리고 그 사이 다른 분이 같은 회차를 저장했다면
   조용히 덮어쓰지 않고 누가 언제 저장했는지 알려 준 뒤 물어봅니다.

   진행 단계 · 단계별 내용 · 추진과제 체크는 프로토타입과 같이 [저장]을 누르지
   않아도 바로 반영됩니다. 회차에 딸린 값이 아니라 사업 자체의 값이기 때문입니다. */
import { useEffect, useMemo, useState } from "react";
import { api, ConflictError, type SaveEntryBody } from "../lib/api";
import { fmtEok, fmtWon } from "../lib/format";
import type { Entry, PeriodOption, ProjectDetail } from "../lib/types";

interface SpendRow {
  amt: string;      // 화면에 보이는 그대로 (1,000,000)
  cat: string;
}

interface Props {
  p: ProjectDetail;
  who: string;
  editingKey: string | null;             // 수정 중인 회차 (없으면 신규)
  onEditingKeyChange: (k: string | null) => void;
  onSaved: (p: ProjectDetail, msg: string, sub: string) => void;
  onConflict: (message: string, sub: string, onOverwrite: () => void) => void;
  onNeedName: () => void;
}

const onlyDigits = (s: string) => s.replace(/[^\d]/g, "");
const commas = (s: string) => (s === "" ? "" : Number(s).toLocaleString("ko-KR"));

export default function InputPanel({
  p, who, editingKey, onEditingKeyChange, onSaved, onConflict, onNeedName,
}: Props) {
  const [periods, setPeriods] = useState<PeriodOption[]>([]);
  const [selected, setSelected] = useState("");
  const [spends, setSpends] = useState<SpendRow[]>([{ amt: "", cat: "" }]);
  const [kpi, setKpi] = useState<Record<string, string>>({});
  const [act, setAct] = useState("");
  const [issue, setIssue] = useState("");
  const [plan, setPlan] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const editing = editingKey !== null;

  // 사업의 비목 목록. 예전에 입력한 비목이 목록에서 빠졌더라도 값이 바뀌지 않도록 함께 넣습니다.
  const catOptions = useMemo(() => {
    const list = p.categories.map((c) => c.name);
    spends.forEach((s) => { if (s.cat && !list.includes(s.cat)) list.push(s.cat); });
    return list;
  }, [p.categories, spends]);

  useEffect(() => {
    let alive = true;
    api.periods(p.id).then((list) => {
      if (!alive) return;
      setPeriods(list);
      setSelected((cur) => (editingKey ?? (cur && list.some((o) => o.key === cur) ? cur : list[0]?.key ?? "")));
    }).catch(() => {});
    return () => { alive = false; };
  }, [p.id, p.entries.length, editingKey]);

  // 수정 모드로 들어오면 그 회차 내용을 폼에 채웁니다
  const target = editing ? editingKey! : selected;
  const cur: Entry | undefined = editing
    ? p.entries.find((e) => e.periodKey === editingKey)
    : undefined;

  useEffect(() => {
    if (cur) {
      setSpends(cur.spends.length
        ? cur.spends.map((s) => ({ amt: commas(String(s.amt)), cat: s.cat }))
        : [{ amt: "", cat: "" }]);
      setKpi(Object.fromEntries(p.kpis.map((k) => [k.name, String(cur.kpi[k.name] ?? "")])));
      setAct(cur.act); setIssue(cur.issue); setPlan(cur.plan);
    } else {
      setSpends([{ amt: "", cat: "" }]);
      setKpi({}); setAct(""); setIssue(""); setPlan("");
    }
    setErr("");
  }, [editingKey, cur?.version]);   // eslint-disable-line react-hooks/exhaustive-deps

  const sum = useMemo(() => {
    let total = 0, bad = false;
    spends.forEach((r) => {
      if (r.amt === "") return;
      const v = Number(r.amt.replace(/,/g, ""));
      if (Number.isNaN(v) || v < 0) bad = true; else total += v;
    });
    return { total, bad };
  }, [spends]);

  // ----- 즉시 저장되는 것들 -----
  async function immediate(run: () => Promise<ProjectDetail>, what: string) {
    if (!who) { onNeedName(); return; }
    try {
      const next = await run();
      onSaved(next, "", what);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "저장하지 못했습니다.");
    }
  }

  // ----- 저장 -----
  function collect(): SaveEntryBody | null {
    const rows: { cat: string; amt: number }[] = [];
    for (const r of spends) {
      if (r.amt === "") continue;
      const v = Number(r.amt.replace(/,/g, ""));
      if (Number.isNaN(v) || v < 0) {
        setErr("집행액은 0 이상의 숫자로 입력하세요."); return null;
      }
      if (v > 0) rows.push({ cat: r.cat || catOptions[0] || "", amt: v });
    }

    const kpiVals: Record<string, number> = {};
    for (const k of p.kpis) {
      const t = (kpi[k.name] ?? "").trim();
      const v = t === "" ? 0 : Number(t.replace(/,/g, ""));
      if (Number.isNaN(v) || v < 0) {
        setErr(`성과지표 '${k.name}' 값을 숫자로 입력하세요.`); return null;
      }
      kpiVals[k.name] = v;
    }
    setErr("");

    const known = periods.find((o) => o.key === target);
    return {
      spends: rows, kpi: kpiVals,
      act: act.trim(), issue: issue.trim(), plan: plan.trim(),
      // 수정 중이면 지금 보고 있는 회차의 번호, 신규면 0
      baseVersion: editing ? (cur?.version ?? 0) : (known?.hasEntry ? 0 : 0),
    };
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    if (!who) { onNeedName(); return; }
    const payload = collect();
    if (!payload) return;

    const send = async (base: number) => {
      setBusy(true);
      try {
        const r = await api.saveEntry(p.id, target, who, { ...payload, baseVersion: base });
        const b = r.project;
        onSaved(b, "저장되었습니다",
          b.rate > 100 ? "집행 누계가 총 사업비를 초과했습니다."
                       : (periods.find((o) => o.key === target)?.label ?? ""));
        onEditingKeyChange(null);
      } catch (ex) {
        if (ex instanceof ConflictError) {
          const info = ex.info;
          onConflict(
            info.message,
            info.kind === "exists"
              ? "기존 내용을 이번 입력으로 바꿉니다. 집행액은 더해지지 않고 교체됩니다."
              : `${info.who} 님이 저장한 내용을 이번 입력으로 바꿉니다.`,
            () => void send(info.current.version)
          );
        } else {
          setErr(ex instanceof Error ? ex.message : "저장하지 못했습니다.");
        }
      } finally {
        setBusy(false);
      }
    };
    await send(payload.baseVersion);
  }

  return (
    <form className="panel" id="weeklyForm" autoComplete="off" onSubmit={submit}>
      <h2>
        <span id="panelTitle">{p.cycleWord} 입력</span>{" "}
        <span className={"badge" + (editing ? " edit" : "")} id="wkModeBadge">
          {editing ? "수정" : "신규"}
        </span>
      </h2>

      <div className="sec">
        <div className="cap">보고 회차</div>
        <select id="wkPeriod" aria-label="보고 회차 선택" value={target} disabled={editing}
                onChange={(e) => setSelected(e.target.value)}>
          {periods.map((o) => (
            <option key={o.key} value={o.key}>{o.full}{o.hasEntry ? " · 입력됨" : ""}</option>
          ))}
          {editing && !periods.some((o) => o.key === editingKey) && (
            <option value={editingKey!}>{cur?.periodFull}</option>
          )}
        </select>
      </div>

      <div className="sec">
        <div className="cap">1 · 진행 단계</div>
        <select id="wkStage" aria-label="현재 진행 단계 선택" value={p.stage}
                onChange={(e) => immediate(
                  () => api.setStage(p.id, Number(e.target.value), who), "진행 단계를 바꿨습니다")}>
          {p.stages.map((nm, i) => <option key={nm} value={i}>{nm}</option>)}
        </select>
        <div id="wkStageNotes" style={{ marginTop: 10 }}>
          {p.stages.map((nm, i) => (
            <div key={nm} className={"stage-in " + (i === p.stage ? "now" : "")}>
              <span className="nm">{nm}</span>
              {/* 입력 중 화면이 다시 그려지지 않도록 포커스가 빠질 때 저장합니다 */}
              <input type="text" defaultValue={p.stageNotes[i] || ""} placeholder="진행 내용"
                     key={`${i}-${p.stageNotes[i]}`}
                     onBlur={(e) => {
                       const v = e.target.value.trim();
                       if (v !== (p.stageNotes[i] || "")) {
                         void immediate(() => api.setStageNote(p.id, i, v, who), "단계 내용을 저장했습니다");
                       }
                     }} />
            </div>
          ))}
        </div>
      </div>

      <div className="sec">
        <div className="cap">2 · 주요 추진과제 체크</div>
        <div id="wkTasks">
          {p.tasks.map((t, i) => (
            <label key={i} className={"chk " + (t.done ? "done" : "")}>
              <input type="checkbox" checked={t.done}
                     onChange={(e) => immediate(
                       () => api.setTask(p.id, i, e.target.checked, who), "추진과제를 저장했습니다")} />
              <span>{t.name}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="sec">
        <div className="cap">3 · 집행액</div>
        <div id="wkSpends">
          {spends.map((r, i) => (
            <div key={i} className="spend-row">
              <input type="text" inputMode="numeric" className="sp-amt" placeholder="원" value={r.amt}
                     onChange={(e) => setSpends(spends.map((x, j) =>
                       j === i ? { ...x, amt: commas(onlyDigits(e.target.value)) } : x))} />
              <select className="sp-cat" value={r.cat || catOptions[0] || ""}
                      onChange={(e) => setSpends(spends.map((x, j) =>
                        j === i ? { ...x, cat: e.target.value } : x))}>
                {catOptions.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
              <button type="button" className="rm" aria-label="집행 항목 삭제"
                      onClick={() => {
                        const next = spends.filter((_, j) => j !== i);
                        setSpends(next.length ? next : [{ amt: "", cat: "" }]);  // 최소 한 줄은 남깁니다
                      }}>×</button>
            </div>
          ))}
        </div>
        <button type="button" className="btn-add"
                onClick={() => setSpends([...spends, { amt: "", cat: "" }])}>+ 집행 항목 추가</button>
        <div className="spend-sum" id="wkSpendSum">
          {sum.bad ? <>회차 합계 <b>—</b></>
                   : <>회차 합계 <b>{fmtWon(sum.total)}</b> 원 ({fmtEok(sum.total)})</>}
        </div>
      </div>

      <div className="sec">
        <div className="cap">4 · 활동 요약</div>
        <input type="text" id="wkAct" placeholder="예: 협력기관 실무 화상회의"
               value={act} onChange={(e) => setAct(e.target.value)} />
      </div>

      <div className="sec">
        <div className="cap">5 · 성과지표 실적</div>
        <div id="wkKpis">
          {p.kpis.map((k) => (
            <div key={k.name} className="kpi-in">
              <span className="nm" title={k.name}>
                {k.name}{" "}
                <small style={{ color: "var(--muted)" }}>(누계 {k.value.toLocaleString()}{k.unit})</small>
              </span>
              <input type="text" inputMode="decimal" placeholder="회차 실적"
                     value={kpi[k.name] ?? ""}
                     onChange={(e) => setKpi({ ...kpi, [k.name]: e.target.value })} />
            </div>
          ))}
        </div>
      </div>

      <div className="sec">
        <div className="cap">6 · 확인사항</div>
        <input type="text" id="wkIssue" placeholder="내용"
               value={issue} onChange={(e) => setIssue(e.target.value)} />
        <input type="text" id="wkActionPlan" placeholder="조치 계획" style={{ marginTop: 8 }}
               value={plan} onChange={(e) => setPlan(e.target.value)} />
      </div>

      <div className={"form-err" + (err ? " on" : "")} id="wkErr">{err}</div>
      <button type="submit" className="btn-primary" disabled={busy}>{busy ? "저장 중…" : "저장"}</button>
      <button type="button" className={"btn-cancel" + (editing ? " on" : "")} id="wkCancel"
              onClick={() => onEditingKeyChange(null)}>수정 취소</button>
    </form>
  );
}
