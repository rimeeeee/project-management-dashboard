/* 일정 달력 — 프로토타입 renderCal() 을 그대로 옮긴 것입니다.

   가장 조심해야 할 부분은 사업 진행 기간을 나타내는 '형광펜 띠'입니다.
   날짜 칸마다 따로 그리면 칸 사이 여백에서 띠가 끊겨 이음매가 지저분해집니다.
   그래서 한 주에 막대 하나로 이어 그립니다. 이 규칙은 되돌아간 적이 있으니
   바꾸지 마세요.

   이전달·다음달 칸은 날짜 글자가 흐린데, 띠를 주 단위로 하나씩 긋기 때문에
   칸마다 색을 다르게 줄 수가 없습니다. 그래서 그 구간 위에 배경색 반투명
   덮개(week-dim)를 씌워 같은 정도로 흐리게 만듭니다. */
import { clamp, daysBetween, isoOf, todayISO } from "../lib/format";

/* 사업 띠 색 — 사업 순서대로 돌아가며 씁니다.
   범례에 이미 쓰는 청록(시작)·빨강(종료)·보라(할 일)는 넣지 않습니다.
   사업이 6개를 넘으면 색이 다시 돌아옵니다. */
export const RUN_COLORS = ["#e0a112", "#e0629b", "#3f9142", "#b5651d", "#4a7fe0", "#00897b"];
export const runColor = (i: number) => RUN_COLORS[i % RUN_COLORS.length];

export interface CalEvent {
  date: string;
  kind: "start" | "end" | "todo";
  label: string;
  pid?: string;
  /* 그 일정이 어느 사업 것인지 색으로 알려 줍니다.
     사업 기간 띠와 같은 색을 써서, 여러 사업이 섞인 전체 화면에서
     '이 할 일이 어느 사업 것인지' 를 색만 보고 알 수 있게 합니다. */
  color?: string;
}

export interface CalRun {
  from: string;
  to: string;
  name: string;
  color: string;
}

interface Props {
  ym: Date;                       // 보고 있는 달 (그 달 1일)
  picked: string;                 // 고른 날짜 (없으면 "")
  big: boolean;                   // '크게 보기' 인지
  events: CalEvent[];
  runs: CalRun[];
  showRunLegend: boolean;         // 사업이 여럿인 전체 화면에서만 띠 범례를 답니다
  onPick: (iso: string) => void;
  onGo?: (pid: string) => void;   // 일정 목록에서 사업 이름을 누르면 이동
  /* 빈 날짜도 고를 수 있게 할지.
     원래는 '그 날 일정을 보려고' 누르는 것이라 일정이 있는 날만 눌렸습니다.
     사업 대시보드에서는 고른 날짜가 할 일 기한이 되므로, 아무것도 없는
     날짜야말로 눌러야 합니다. 그 화면에서만 켭니다. */
  pickAnyDay?: boolean;
  idSuffix: string;               // home / dash / full
}

export default function Calendar({
  ym, picked, big, events, runs, showRunLegend, onPick, onGo, idSuffix, pickAnyDay = false,
}: Props) {
  const 연 = ym.getFullYear();
  const 월 = ym.getMonth();

  const 날짜별: Record<string, CalEvent[]> = {};
  events.forEach((e) => {
    (날짜별[e.date] = 날짜별[e.date] || []).push(e);
  });

  const 첫날 = new Date(연, 월, 1);
  const 시작 = new Date(연, 월, 1 - 첫날.getDay());   // 그 주 일요일부터
  const 오늘 = todayISO();
  const 날더하기 = (n: number) =>
    new Date(시작.getFullYear(), 시작.getMonth(), 시작.getDate() + n);
  const 화면첫날 = isoOf(시작);
  const 화면끝날 = isoOf(날더하기(41));

  /* 이 화면에 걸치는 사업만 골라 사업마다 고정된 줄(레인)을 줍니다.
     그래야 주가 바뀌어도 같은 사업이 늘 같은 높이에 놓입니다. */
  const 레인 = runs
    .filter((r) => !(r.to < 화면첫날 || r.from > 화면끝날))
    .slice(0, 6);   // 너무 많으면 칸이 길어지므로 6개까지만

  const 주들 = [];
  for (let w = 0; w < 6; w++) {
    const 주시작 = isoOf(날더하기(w * 7));
    const 주끝 = isoOf(날더하기(w * 7 + 6));
    const 칸 = [];
    const 딴달: number[] = [];   // 이번 달이 아닌 칸 번호

    for (let c2 = 0; c2 < 7; c2++) {
      const d = 날더하기(w * 7 + c2);
      const iso = isoOf(d);
      const 이번달 = d.getMonth() === 월;
      if (!이번달) 딴달.push(c2);
      const 목록 = 날짜별[iso] || [];
      const 종류 = [...new Set(목록.map((e) => e.kind))];
      const 표시 = [
        이번달 ? "" : "out",
        d.getDay() === 0 ? "sun" : "",
        iso === 오늘 ? "today" : "",
        목록.length ? "has" : "",
        iso === picked ? "sel" : "",
      ].filter(Boolean).join(" ");

      const 누를수있음 = pickAnyDay || 목록.length > 0;
      칸.push(
        <div
          key={iso}
          className={"cal-d " + 표시}
          title={목록.length ? 목록.map((e) => e.label).join(" / ") : ""}
          {...(누를수있음
            ? {
                role: "button",
                tabIndex: 0,
                onClick: () => onPick(iso),
                onKeyDown: (ev: React.KeyboardEvent) => {
                  if (ev.key === "Enter" || ev.key === " ") {
                    ev.preventDefault();
                    onPick(iso);
                  }
                },
              }
            : {})}
        >
          {d.getDate()}
          <span className="cal-dots">
            {종류.map((k) => {
              // 할 일 점은 그 사업의 띠 색을 그대로 씁니다(같은 날 여러 사업이면 첫 번째).
              const 색 = k === "todo" ? 목록.find((e) => e.kind === "todo")?.color : undefined;
              return <i key={k} className={"dot-" + k} style={색 ? { background: 색 } : undefined} />;
            })}
          </span>
          {목록.length > 0 && (
            <span className="cal-lbl">
              {목록[0].label}{목록.length > 1 ? ` 외 ${목록.length - 1}` : ""}
            </span>
          )}
        </div>
      );
    }

    // 이 주에 걸치는 사업을 한 줄짜리 막대 하나로 그립니다
    const 띠들 = 레인.map((r, li) => {
      if (r.to < 주시작 || r.from > 주끝) return <span key={li} className="rr" />;
      const 시작칸 = Math.max(0, daysBetween(주시작, r.from));
      const 끝칸 = Math.min(6, daysBetween(주시작, r.to));
      const 왼쪽 = (시작칸 / 7) * 100;
      const 너비 = ((끝칸 - 시작칸 + 1) / 7) * 100;
      const 끝맺음 = (r.from >= 주시작 ? " s" : "") + (r.to <= 주끝 ? " e" : "");
      return (
        <span key={li} className="rr">
          <i
            className={끝맺음.trim()}
            style={{ left: `${왼쪽}%`, width: `${너비}%`, background: r.color }}
            title={r.name}
          />
        </span>
      );
    });

    // 이어진 '딴달' 구간을 묶어 덮개 하나로 만듭니다
    const 덮개 = [];
    for (let k = 0; k < 딴달.length; ) {
      let j = k;
      while (j + 1 < 딴달.length && 딴달[j + 1] === 딴달[j] + 1) j++;
      const 왼쪽 = (딴달[k] / 7) * 100;
      const 너비 = ((딴달[j] - 딴달[k] + 1) / 7) * 100;
      덮개.push(
        <span key={`dim${k}`} className="week-dim" style={{ left: `${왼쪽}%`, width: `${너비}%` }} />
      );
      k = j + 1;
    }

    주들.push(
      <div key={w} className="cal-week">
        {칸}
        {레인.length > 0 && <span className="week-runs">{띠들}{덮개}</span>}
      </div>
    );
  }

  // 범례 — 띠 색이 어느 사업인지 알려 줍니다
  const 본이름 = new Set<string>();
  const 띠범례: CalRun[] = [];
  runs.forEach((r) => {
    if (본이름.has(r.name)) return;
    본이름.add(r.name);
    띠범례.push(r);
  });

  // 아래 목록: 날짜를 고르면 그 날, 아니면 이번 달 전체
  const 이달 = `${연}-${String(월 + 1).padStart(2, "0")}`;
  const 대상 = (picked
    ? events.filter((e) => e.date === picked)
    : events.filter((e) => e.date.slice(0, 7) === 이달)
  ).slice().sort((a, b) => (a.date < b.date ? -1 : 1));

  /* 작게 볼 때는 목록이 길어지면 화면을 다 잡아먹어서,
     지난 일정은 접고 5건까지만 보여 줍니다. */
  let 보일것 = 대상;
  let 더 = 0;
  if (!big && !picked) {
    const 앞으로 = 대상.filter((e) => e.date >= 오늘);
    보일것 = 앞으로.length ? 앞으로 : 대상.slice(-5);
    더 = Math.max(0, 보일것.length - 5);
    보일것 = 보일것.slice(0, 5);
  }

  return (
    <>
      <div className="cal-grid" id={"calGrid-" + idSuffix}
           style={{ ["--runrows" as string]: String(레인.length) }}>
        {주들}
      </div>

      <div className="cal-legend" id={"calLegend-" + idSuffix}>
        <div className="row">
          <span><i className="k-start" />사업 시작</span>
          <span><i className="k-end" />사업 종료</span>
          {/* 할 일 점은 그 사업의 색을 씁니다. 사업이 하나면 그 색을 그대로 보여 주고,
              여럿이면 색이 제각각이라 '사업 색' 이라고만 적습니다. */}
          {runs.length === 1
            ? <span><i className="k-todo" style={{ background: runs[0].color }} />할 일 기한</span>
            : <span><i className="k-todo" />할 일 기한 <span className="k-note">(사업 색)</span></span>}
        </div>
        {/* 사업 대시보드에서는 사업이 하나뿐이고 이름이 화면 제목에 이미 있으므로
            사업 범례 줄을 넣지 않습니다. */}
        {showRunLegend && 띠범례.length > 0 && (
          <div className="row runs">
            {띠범례.map((r) => (
              <span key={r.name} className="run-key">
                <i style={{ background: r.color }} />{r.name}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="cal-events" id={"calEvents-" + idSuffix}>
        <div className="cat-head" style={{ marginBottom: 0 }}>일정 {대상.length}건</div>
        {보일것.length ? (
          <>
            {보일것.map((e, i) => (
              <div key={i} className="cal-ev">
                <i className={"dot-" + e.kind}
                   style={e.kind === "todo" && e.color ? { background: e.color } : undefined} />
                <span className="d">{e.date.slice(5).replaceAll("-", ".")}</span>
                <span className="nm">
                  {e.pid && onGo ? (
                    <button type="button" className="home-name" onClick={() => onGo(e.pid!)}>
                      {e.label}
                    </button>
                  ) : e.label}
                </span>
              </div>
            ))}
            {더 > 0 && (
              <div className="cal-more">외 {더}건 — '크게 보기'에서 모두 볼 수 있습니다</div>
            )}
          </>
        ) : (
          <div className="empty">이 달에는 표시할 일정이 없습니다.</div>
        )}
      </div>
    </>
  );
}

/* 달력이 보여 줄 일정(점)과 진행 기간(형광펜)을 사업 목록에서 뽑습니다.
   프로토타입 calData() 와 같습니다.

   공고 마감일은 넣지 않습니다. 달력은 '내 사업' 목록에 등록한 사업만 다룹니다.
   아직 우리 사업이 아닌 공고까지 섞이면 정작 봐야 할 사업 일정이 묻힙니다.
   공고 마감은 '사업 현황(공고)' 화면에서 마감 임박순과 D-day 로 봅니다. */
export function calData(
  projects: { id: string; name: string; start: string; end: string; todos?: { due: string; text: string; done: boolean }[] }[],
  allProjects: { id: string }[]
): { events: CalEvent[]; runs: CalRun[] } {
  const events: CalEvent[] = [];
  const runs: CalRun[] = [];
  projects.forEach((p, i) => {
    if (p.start) events.push({ date: p.start, kind: "start", label: `${p.name} 시작`, pid: p.id });
    if (p.end) events.push({ date: p.end, kind: "end", label: `${p.name} 종료`, pid: p.id });
    if (p.start && p.end) {
      // 대시보드(사업 1건)에서도 전체 목록에서의 순서를 써야 색이 같습니다
      const idx = allProjects.findIndex((x) => x.id === p.id);
      runs.push({ from: p.start, to: p.end, name: p.name, color: runColor(idx >= 0 ? idx : i) });
    }
    const 사업색 = runColor(allProjects.findIndex((x) => x.id === p.id) >= 0
      ? allProjects.findIndex((x) => x.id === p.id) : i);
    (p.todos || []).forEach((t) => {
      if (t.due && !t.done) {
        events.push({ date: t.due, kind: "todo", label: `할 일 · ${t.text}`, pid: p.id, color: 사업색 });
      }
    });
  });
  return { events, runs };
}

export { clamp };
