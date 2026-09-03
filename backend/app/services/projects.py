"""
사업 조회 — 화면에 필요한 모양으로 만들어 줍니다.

계산 규칙(진행률·상태·집행률)은 서버에서 한 번만 계산해 내려보냅니다.
프로토타입은 브라우저에서 계산했는데, 규칙이 두 군데 있으면 한쪽만 고쳐져
숫자가 어긋나기 쉽습니다. 규칙은 backend/app/core/calc.py 한 곳에만 둡니다.

화면에서 하는 것은 '표시'뿐입니다 — 원 단위를 억으로 바꿔 적는 것 같은 일입니다.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.core import calc
from app.core.config import KST
from app.core.periods import cycle_word, period_of
from app.models import Project, ReportEntry


def _iso(d: date | None) -> str:
    return d.isoformat() if d else ""


def dday(end: date, at: datetime | None = None) -> dict[str, str]:
    """
    프로토타입 ddayText() — 종료일 23:59:59 까지 남은 날수를 올림합니다.
    """
    at = at or calc.now()
    end_dt = datetime.combine(end, datetime.max.time().replace(microsecond=0), tzinfo=KST)
    days = -((at - end_dt) // timedelta(days=1))   # JS Math.ceil 과 같게
    if days < 0:
        return {"txt": "종료", "cls": "closed"}
    if days == 0:
        return {"txt": "D-day", "cls": "soon"}
    if days <= 30:
        return {"txt": f"D-{days}", "cls": "soon"}
    return {"txt": f"D-{days}", "cls": "open"}


def entry_total(e: ReportEntry) -> int:
    """한 회차의 집행 합계 (원)"""
    return sum(s.amount for s in e.spends)


def cat_summary(e: ReportEntry) -> str:
    """입력 내역 표의 비목 요약: '장비·재료비 외 2'"""
    if not e.spends:
        return "-"
    if len(e.spends) == 1:
        return e.spends[0].category
    return f"{e.spends[0].category} 외 {len(e.spends) - 1}"


def has_issue_text(e: ReportEntry) -> bool:
    return bool(e.issue and e.issue.strip())


def open_issues(p: Project) -> list[ReportEntry]:
    """아직 해결되지 않은 확인사항 (상태 판정에 씁니다)"""
    return [e for e in sorted(p.entries, key=lambda x: x.entry_date)
            if has_issue_text(e) and not e.issue_done]


def latest_issue(p: Project) -> ReportEntry | None:
    lst = open_issues(p)
    return lst[-1] if lst else None


def _core_numbers(p: Project) -> dict[str, Any]:
    total = len(p.tasks)
    done = sum(1 for t in p.tasks if t.done)
    actual = calc.calc_actual(total, done)
    planned = calc.calc_planned(p.start, p.end)
    st = calc.calc_status(actual, planned, bool(open_issues(p)))
    spent = sum(entry_total(e) for e in p.entries)
    rate = (spent / p.budget * 100) if p.budget > 0 else 0.0
    return {
        "actual": actual,
        "planned": planned,
        "diff": actual - planned,
        "status": {"key": st.key, "label": st.label},
        # 진행률 숫자·게이지 색은 계획 대비만 봅니다 (확인사항 미반영).
        # 상태 배지와 기준이 다르므로 따로 내려보냅니다.
        "progressColor": calc.progress_color(actual, planned),
        "tasksDone": done,
        "tasksTotal": total,
        "spent": spent,
        "rate": rate,
        "left": max(0, p.budget - spent),
    }


def _stage_rows(p) -> list[dict]:
    """
    단계별 완료 집계. '지금 어느 단계인지' 도 여기서 정합니다.

    현재 단계 = 아직 끝나지 않은 과제가 처음 나오는 단계.
    사람이 손으로 골라 두면 바꾸는 것을 잊어 실제와 어긋나므로 계산해서 씁니다.
    (예전 값 p.stage 는 그대로 두어, 필요하면 견주어 볼 수 있게 합니다)
    """
    묶음: dict[int, list] = {i: [] for i in range(len(calc.STAGES))}
    for t in p.tasks:
        묶음.setdefault(t.stage, []).append(t)

    현재 = None
    for i in sorted(묶음):
        if any(not t.done for t in 묶음[i]):
            현재 = i
            break
    if 현재 is None and any(묶음.values()):
        현재 = max(i for i, v in 묶음.items() if v)      # 다 끝났으면 마지막 단계

    rows = []
    for i, name in enumerate(calc.STAGES):
        items = 묶음.get(i, [])
        done = sum(1 for t in items if t.done)
        rows.append({
            "name": name,
            "done": done,
            "total": len(items),
            "rate": calc.js_round(100 * done / len(items)) if items else 0,
            "current": i == 현재,
        })
    return rows


def summary(p: Project) -> dict[str, Any]:
    """전체 사업 현황 표와 왼쪽 사업 목록에서 쓰는 모양"""
    iss = latest_issue(p)
    return {
        "id": p.id,
        "name": p.name,
        "agency": p.agency,
        "start": _iso(p.start),
        "end": _iso(p.end),
        "budget": p.budget,
        "cycle": p.cycle,
        "cycleWord": cycle_word(p.cycle),
        "dday": dday(p.end),
        "latestIssue": iss.issue if iss else "",
        **_core_numbers(p),
    }


def _entry_out(p: Project, e: ReportEntry) -> dict[str, Any]:
    per = period_of(p.cycle, p.start, e.entry_date)
    return {
        "periodKey": e.period_key,
        "date": _iso(e.entry_date),
        "periodLabel": per.label,
        "periodFull": per.full,
        "spends": [{"cat": s.category, "amt": s.amount} for s in e.spends],
        "spendTotal": entry_total(e),
        "catSummary": cat_summary(e),
        "kpi": {kv.kpi_name: kv.value for kv in e.kpi_values},
        "act": e.act,
        "issue": e.issue,
        "plan": e.plan,
        "issueDone": e.issue_done,
        "version": e.version,
    }


def detail(p: Project) -> dict[str, Any]:
    """사업 대시보드 한 화면에 필요한 것 전부"""
    entries = sorted(p.entries, key=lambda e: e.entry_date)

    # 비목별 사용액. 사업 등록에서 지운 비목이라도 이미 쓴 돈이 있으면 보여 줘야 합니다.
    by_cat: dict[str, int] = {}
    for e in entries:
        for s in e.spends:
            by_cat[s.category] = by_cat.get(s.category, 0) + s.amount

    allocated = {c.name: c.budget_amount for c in p.categories}
    names = list(allocated.keys()) + [n for n in by_cat if n not in allocated]
    cats = [
        {"name": n, "used": by_cat.get(n, 0), "allocated": allocated.get(n, 0)}
        for n in names
    ]
    # 프로토타입과 같은 정렬: 배정액(없으면 사용액)이 큰 것부터
    cats = [c for c in cats if c["used"] > 0 or c["allocated"] > 0]
    cats.sort(key=lambda c: c["allocated"] or c["used"], reverse=True)

    kpis = []
    for k in p.kpis:
        value = sum(kv.value for e in entries for kv in e.kpi_values if kv.kpi_name == k.name)
        kpis.append({"name": k.name, "unit": k.unit, "target": k.target, "value": value})

    return {
        **summary(p),
        "folderUrl": p.folder_url,
        "stage": p.stage,
        "stages": calc.STAGES,
        "stageNotes": [n.note for n in sorted(p.stage_notes, key=lambda x: x.stage_index)],
        "categories": [
            {"name": c.name, "allocated": c.budget_amount} for c in p.categories
        ],
        "catRows": cats,
        "tasks": [
            {"name": t.name, "done": t.done, "stage": t.stage}
            for t in sorted(p.tasks, key=lambda x: (x.sort_order, x.id))
        ],
        # 단계별로 몇 건 중 몇 건이 끝났는지. 전체 진행률과 달리 '어느 구간에서
        # 막혀 있는지' 를 봅니다. 과제가 하나도 없는 단계는 count 0 으로 나가고
        # 화면에서 '과제 없음' 으로 적습니다.
        "stageRows": _stage_rows(p),
        "kpis": kpis,
        "todos": [
            {"id": t.id, "text": t.text, "due": _iso(t.due), "done": t.done}
            for t in p.todos
        ],
        "entries": [_entry_out(p, e) for e in entries],
    }
