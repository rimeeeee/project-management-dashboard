/* 신규 사업 등록 · 사업 정보 수정 — 프로토타입 initRegForm() / editProject() /
   submitRegister() 를 옮겼습니다.

   확인 순서와 문구는 프로토타입 그대로입니다(사업명 → 기간 → 총사업비 →
   비목 → 추진과제 → 성과지표). 서버에서도 같은 순서로 다시 확인합니다.

   금액은 총 사업비도 비목 배정액도 모두 원 단위로 받습니다. */
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { ProjectDetail } from "../lib/types";

const CYCLE_HELP: Record<string, string> = {
  "주간": "월요일~일요일 단위로 회차를 계산합니다.",
  "격주": "사업 시작일부터 2주 단위로 회차를 계산합니다.",
  "월간": "매월 1일~말일 단위로 회차를 계산합니다.",
};

// 새 사업을 만들 때 기본으로 채워지는 비목 — 등록 화면에서 바꿀 수 있습니다
const DEFAULT_CATEGORIES = ["인건비", "연구활동비", "장비·재료비", "여비", "회의·행사비", "외주용역비", "기타"];

interface KpiRow { name: string; target: string; unit: string }
interface CatRow { name: string; amt: string }

/* 공고에서 [사업 등록] 을 눌렀을 때 미리 채워 넣는 값.
   공고 목록에는 사업 기간·추진과제가 없으므로 채울 수 있는 것만 채웁니다. */
export interface Prefill {
  name: string;
  agency: string;
  budget: string;      // 원, 화면에 보이는 그대로
}

interface Props {
  editing: ProjectDetail | null;     // null 이면 신규 등록
  prefill?: Prefill | null;
  onSaved: (p: ProjectDetail, msg: string, sub: string) => void;
  onDeleted: (name: string) => void;
  onCancel: () => void;
  onModal: (msg: string, sub?: string, onOk?: () => void, danger?: boolean) => void;
}

const onlyDigits = (s: string) => s.replace(/[^\d]/g, "");
const commas = (s: string) => (s === "" ? "" : Number(s).toLocaleString("ko-KR"));

export default function Register({ editing, prefill, onSaved, onDeleted, onCancel, onModal }: Props) {
  const [name, setName] = useState("");
  const [agency, setAgency] = useState("");
  const [folder, setFolder] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [budget, setBudget] = useState("");
  const [cycle, setCycle] = useState("주간");
  const [kpis, setKpis] = useState<KpiRow[]>([]);
  /* 과제는 이름과 단계를 함께 들고 있습니다. 과제를 새로 더하면 바로 위
     과제와 같은 단계로 시작해서, 단계가 바뀌는 곳만 고르면 됩니다. */
  const [tasks, setTasks] = useState<{ name: string; stage: number }[]>([]);
  const [cats, setCats] = useState<CatRow[]>([]);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (editing) {
      setName(editing.name);
      setAgency(editing.agency);
      setFolder(editing.folderUrl);
      setStart(editing.start);
      setEnd(editing.end);
      setBudget(editing.budget ? editing.budget.toLocaleString("ko-KR") : "");
      setCycle(editing.cycle);
      setKpis(editing.kpis.length
        ? editing.kpis.map((k) => ({ name: k.name, target: String(k.target), unit: k.unit }))
        : [{ name: "", target: "", unit: "" }]);
      setTasks(editing.tasks.length
        ? editing.tasks.map((t) => ({ name: t.name, stage: t.stage }))
        : [{ name: "", stage: 1 }]);
      setCats(editing.categories.length
        ? editing.categories.map((c) => ({ name: c.name, amt: c.allocated ? commas(String(c.allocated)) : "" }))
        : [{ name: "", amt: "" }]);
    } else {
      // 공고에서 넘어왔으면 옮겨 온 값으로 시작합니다
      setName(prefill?.name ?? "");
      setAgency(prefill?.agency ?? "");
      setBudget(prefill?.budget ?? "");
      setFolder(""); setStart(""); setEnd("");
      setCycle("주간");
      setKpis(Array.from({ length: 4 }, () => ({ name: "", target: "", unit: "" })));
      setTasks(Array.from({ length: 4 }, () => ({ name: "", stage: 1 })));
      setCats(DEFAULT_CATEGORIES.map((c) => ({ name: c, amt: "" })));
    }
    setErr("");
  }, [editing?.id, editing === null, prefill]);   // eslint-disable-line react-hooks/exhaustive-deps

  /* 입력 내역이 있으면 회차 계산 기준은 바꾸지 못하게 막습니다 (기존 회차가 어긋납니다).
     주간·월간 회차 키는 시작일과 상관없으므로 격주일 때만 시작일도 함께 잠급니다. */
  const locked = !!editing && editing.entries.length > 0;
  const startLocked = locked && editing!.cycle === "격주";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setErr("");
    const payload = {
      name, agency, folderUrl: folder, start, end,
      budget: Number(budget.replace(/,/g, "")) || 0,
      cycle,
      kpis: kpis.map((k) => ({
        name: k.name, target: Number(k.target.replace(/,/g, "")) || 0, unit: k.unit,
      })),
      tasks: tasks.map((t) => ({ name: t.name, stage: t.stage })),
      categories: cats.map((c) => ({ name: c.name, amt: c.amt })).map((c) => ({
        name: c.name, allocated: Number(onlyDigits(c.amt)) || 0,
      })),
    };
    try {
      const saved = editing
        ? await api.updateProject(editing.id, payload)
        : await api.createProject(payload);
      onSaved(saved, editing ? "저장되었습니다" : "등록되었습니다", saved.name);
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "저장하지 못했습니다.");
    } finally {
      setBusy(false);
    }
  }

  function remove() {
    if (!editing) return;
    onModal("이 사업을 삭제할까요?",
      `${editing.name} · 입력 내역 ${editing.entries.length}건이 함께 삭제됩니다.`,
      async () => {
        try {
          await api.deleteProject(editing.id);
          onDeleted(editing.name);
        } catch (ex) {
          setErr(ex instanceof Error ? ex.message : "삭제하지 못했습니다.");
        }
      }, true);
  }

  return (
    <section className="view on">
      <div className="page-title" id="regTitle">{editing ? "사업 정보 수정" : "신규 사업 등록"}</div>

      <form className="reg-wrap" id="regForm" autoComplete="off" onSubmit={submit}>
        <div className="card">
          <h2>1 · 기본 정보</h2>
          <div className="f-grid">
            <div className="f" style={{ gridColumn: "1/-1" }}>
              <label htmlFor="rgName">사업명 *</label>
              <input id="rgName" placeholder="예: 연구중심병원 육성(R&D) 협력지원 과제"
                     autoFocus={!!prefill}
                     value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="f" style={{ gridColumn: "1/-1" }}>
              <label htmlFor="rgAgency">발주처</label>
              <input id="rgAgency" placeholder="예: 보건복지부 · 한국보건산업진흥원"
                     value={agency} onChange={(e) => setAgency(e.target.value)} />
            </div>
            <div className="f" style={{ gridColumn: "1/-1" }}>
              <label htmlFor="rgFolder">공유폴더 주소</label>
              <input id="rgFolder" placeholder="예: https://... 또는 \\서버\사업폴더"
                     value={folder} onChange={(e) => setFolder(e.target.value)} />
              <span className="help">넣어 두면 대시보드 아래에서 바로 열 수 있습니다.</span>
            </div>
            <div className="f">
              <label htmlFor="rgStart">사업 시작일 *</label>
              <input id="rgStart" type="date" value={start} disabled={startLocked}
                     onChange={(e) => setStart(e.target.value)} />
              <span className="help" id="startHelp">
                {startLocked ? "입력 내역이 있어 격주 회차 기준일은 변경할 수 없습니다." : ""}
              </span>
            </div>
            <div className="f">
              <label htmlFor="rgEnd">사업 종료일 *</label>
              <input id="rgEnd" type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
            </div>
            <div className="f">
              <label htmlFor="rgBudget">총 사업비 (원) *</label>
              <input id="rgBudget" type="text" inputMode="numeric" placeholder="예: 950000000"
                     value={budget} onChange={(e) => setBudget(e.target.value)} />
            </div>
            <div className="f">
              <label htmlFor="rgCycle">보고 주기</label>
              <select id="rgCycle" value={cycle} disabled={locked}
                      onChange={(e) => setCycle(e.target.value)}>
                <option>주간</option><option>격주</option><option>월간</option>
              </select>
              <span className="help" id="cycleHelp">
                {locked ? "입력 내역이 있어 보고 주기는 변경할 수 없습니다." : CYCLE_HELP[cycle]}
              </span>
            </div>
          </div>
        </div>

        <div className="card">
          <h2>2 · 성과지표 정의</h2>
          <div id="rgKpiRows">
            {kpis.map((k, i) => (
              <div key={i} className="dyn-row">
                <input placeholder="지표명" className="k-nm" value={k.name}
                       onChange={(e) => setKpis(kpis.map((x, j) => j === i ? { ...x, name: e.target.value } : x))} />
                <input placeholder="목표" inputMode="decimal" className="k-tg" value={k.target}
                       onChange={(e) => setKpis(kpis.map((x, j) => j === i ? { ...x, target: e.target.value } : x))} />
                <input placeholder="단위" className="k-un" value={k.unit}
                       onChange={(e) => setKpis(kpis.map((x, j) => j === i ? { ...x, unit: e.target.value } : x))} />
                <button type="button" className="rm" aria-label="지표 삭제"
                        onClick={() => setKpis(kpis.filter((_, j) => j !== i))}>×</button>
              </div>
            ))}
          </div>
          <button type="button" className="btn-add"
                  onClick={() => setKpis([...kpis, { name: "", target: "", unit: "" }])}>+ 지표 추가</button>
          <div className="f" style={{ marginTop: 12 }}>
            <span className="help">실적은 회차마다 발생한 값만 입력하면 자동으로 합산되어 달성률에 반영됩니다.</span>
          </div>
        </div>

        <div className="card">
          <h2>3 · 주요 추진과제</h2>
          <div id="rgTaskRows">
            {tasks.map((t, i) => (
              <div key={i} className="dyn-row task">
                <input placeholder="추진과제" className="t-nm" value={t.name}
                       onChange={(e) => setTasks(tasks.map((x, j) =>
                         j === i ? { ...x, name: e.target.value } : x))} />
                <button type="button" className="rm" aria-label="과제 삭제"
                        onClick={() => setTasks(tasks.filter((_, j) => j !== i))}>×</button>
              </div>
            ))}
          </div>
          <p className="hint" style={{ marginTop: 6 }}>과제는 진행 순서대로 적습니다.</p>
          <button type="button" className="btn-add"
                  onClick={() => setTasks([...tasks,
                    { name: "", stage: tasks.length ? tasks[tasks.length - 1].stage : 1 }])}>
            + 추진과제 추가</button>
        </div>

        <div className="card">
          <h2>4 · 예산 비목 <span className="hint">배정액을 넣으면 비목별 잔액이 표시됩니다</span></h2>
          <div id="rgCatRows">
            {cats.map((c, i) => (
              <div key={i} className="dyn-row cat">
                <input placeholder="비목명 (예: 인건비)" className="c-nm" value={c.name}
                       onChange={(e) => setCats(cats.map((x, j) => j === i ? { ...x, name: e.target.value } : x))} />
                <input placeholder="배정액 (원)" inputMode="numeric" className="c-amt" value={c.amt}
                       onChange={(e) => setCats(cats.map((x, j) =>
                         j === i ? { ...x, amt: commas(onlyDigits(e.target.value)) } : x))} />
                <button type="button" className="rm" aria-label="비목 삭제"
                        onClick={() => setCats(cats.filter((_, j) => j !== i))}>×</button>
              </div>
            ))}
          </div>
          <button type="button" className="btn-add"
                  onClick={() => setCats([...cats, { name: "", amt: "" }])}>+ 비목 추가</button>
        </div>

        <div className={"form-err" + (err ? " on" : "")} id="rgErr">{err}</div>

        <div className="reg-actions">
          <button type="submit" className="btn-primary" id="regSubmit" style={{ marginTop: 0 }} disabled={busy}>
            {busy ? "저장 중…" : (editing ? "저장" : "등록")}
          </button>
          <button type="button" className={"btn-danger" + (editing ? " on" : "")} id="regDelete"
                  onClick={remove}>사업 삭제</button>
          <button type="button" className={"btn-ghost" + (editing ? " on" : "")} id="regCancel"
                  onClick={onCancel}>취소</button>
        </div>
      </form>
    </section>
  );
}
