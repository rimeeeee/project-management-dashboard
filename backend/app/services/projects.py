"""
사업 조회 — 화면에 필요한 모양으로 만들어 줍니다.

계산 규칙(진행률·상태·집행률)은 서버에서 한 번만 계산해 내려보냅니다.
프로토타입은 브라우저에서 계산했는데, 규칙이 두 군데 있으면 한쪽만 고쳐져
숫자가 어긋나기 쉽습니다. 규칙은 backend/app/core/calc.py 한 곳에만 둡니다.

화면에서 하는 것은 '표시'뿐입니다 — 원 단위를 억으로 바꿔 적는 것 같은 일입니다.
"""
from __future__ import annotations

from datetime import date, datetime
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
    # 종료일은 그날 전체를 포함하고, 한국 날짜가 다음 날이 되는 즉시 종료입니다.
    # 시각 차이를 24시간 단위로 내림하면 다음 날에도 D-day로 남는 문제가 생깁니다.
    local_date = at.astimezone(KST).date() if at.tzinfo else at.date()
    days = (end - local_date).days
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
        "spends": [
            {"cat": s.category, "amt": s.amount,
             # 지출일이 없는 것은 이 칸이 생기기 전에 넣은 내역입니다.
             # 회차 날짜로 봅니다.
             "on": _iso(s.spend_on or e.entry_date)}
            for s in e.spends
        ],
        "spendTotal": entry_total(e),
        "catSummary": cat_summary(e),
        "kpi": {kv.kpi_name: kv.value for kv in e.kpi_values},
        "act": e.act,
        "issue": e.issue,
        "plan": e.plan,
        "issueDone": e.issue_done,
        "version": e.version,
    }


def _month(d) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _cat_rows(p: Project, entries) -> list[dict[str, Any]]:
    """
    세목별 편성액·집행액. 산출 근거 쪽지도 함께 냅니다.

    계정과목은 사업마다 하나뿐이라 여기서 묶지 않습니다. 이 사업에서 쓴
    돈은 모두 그 한 과목으로 잡히고, 그 합계는 spent 입니다.
    """
    쓴돈: dict[str, int] = {}
    for e in entries:
        for s in e.spends:
            쓴돈[s.category] = 쓴돈.get(s.category, 0) + s.amount

    행 = [
        {"name": c.name, "allocated": c.budget_amount,
         "gov": c.budget_gov, "own": c.budget_self,
         "used": 쓴돈.get(c.name, 0), "basis": c.basis}
        for c in sorted(p.categories, key=lambda x: (x.sort_order, x.id))
    ]
    있는것 = {c.name for c in p.categories}
    # 사업 등록에서 지운 세목이라도 이미 쓴 돈이 있으면 보여 줍니다.
    # 감추면 합계가 맞지 않아 '어디서 새는 돈' 처럼 보입니다.
    행 += [
        {"name": 이름, "allocated": 0, "gov": 0, "own": 0, "used": 액, "basis": ""}
        for 이름, 액 in 쓴돈.items() if 이름 not in 있는것
    ]

    행 = [r for r in 행 if r["allocated"] > 0 or r["used"] > 0]
    # 프로토타입과 같은 정렬: 편성액(없으면 집행액)이 큰 것부터
    행.sort(key=lambda r: r["allocated"] or r["used"], reverse=True)
    return 행


def _monthly(p: Project, entries) -> dict[str, Any]:
    """
    월별 × 세목 집행액.

    기본적으로 사업 시작 달부터 이번 달 또는 사업 종료 달까지 이어서 냅니다.
    다만 사업 기간 밖에 기록된 지출이 있으면 그 달도 포함해 집행 총액이
    월별 표에서 빠지지 않게 합니다.
    아직 오지 않은 달을 스무 칸씩 늘어놓아 봐야 읽기만 어렵습니다.
    중간에 안 쓴 달은 0 으로 남겨 둡니다 — 빈 달도 알아야 할 사실입니다.
    """
    칸: dict[tuple[str, str], int] = {}
    지출달: list[str] = []
    for e in entries:
        for s in e.spends:
            달 = _month(s.spend_on or e.entry_date)
            칸[(s.category, 달)] = 칸.get((s.category, 달), 0) + s.amount
            지출달.append(달)

    if not p.start:
        return {"months": [], "rows": [], "totals": {}, "grand": 0}

    오늘 = calc.today()
    시작달 = _month(p.start)
    종료달 = _month(p.end) if p.end else _month(오늘)
    기본마지막 = max(시작달, min(_month(오늘), 종료달))
    처음 = min([시작달, *지출달]) if 지출달 else 시작달
    마지막 = max([기본마지막, *지출달]) if 지출달 else 기본마지막

    달들: list[str] = []
    해, 월 = (int(x) for x in 처음.split("-"))
    while f"{해:04d}-{월:02d}" <= 마지막:
        달들.append(f"{해:04d}-{월:02d}")
        월 += 1
        if 월 > 12:
            해, 월 = 해 + 1, 1
    행 = []
    for r in _cat_rows(p, entries):
        이름 = r["name"]
        by = {m: 칸.get((이름, m), 0) for m in 달들}
        if sum(by.values()) == 0:
            continue          # 한 푼도 안 쓴 세목은 표를 늘리기만 합니다
        행.append({"cat": 이름, "byMonth": by, "total": sum(by.values())})

    합 = {m: sum(r["byMonth"][m] for r in 행) for m in 달들}
    return {"months": 달들, "rows": 행, "totals": 합, "grand": sum(합.values())}


def detail(p: Project) -> dict[str, Any]:
    """사업 대시보드 한 화면에 필요한 것 전부"""
    entries = sorted(p.entries, key=lambda e: e.entry_date)

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
        # 계정과목은 사업마다 하나입니다. 이 사업에서 쓴 돈은 모두
        # 이 과목으로 잡히고, 그 합계가 spent 입니다.
        "account": p.account,
        "categories": [
            # allocated 는 gov + own 입니다. 화면 숫자는 이 합계를 쓰고,
            # 나눈 둘은 사업을 고칠 때 입력칸을 다시 채우는 데 씁니다.
            {"name": c.name, "allocated": c.budget_amount,
             "gov": c.budget_gov, "own": c.budget_self, "basis": c.basis}
            for c in p.categories
        ],
        # 세목별 편성액·집행액·산출 근거.
        "catRows": _cat_rows(p, entries),
        # 월별 × 세목 집행액.
        "monthly": _monthly(p, entries),
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
