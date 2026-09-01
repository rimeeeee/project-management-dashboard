"""
옮긴 로직이 프로토타입과 같은 값을 내는지 확인합니다.

    .venv/bin/python scripts/verify/run.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

for _s in (sys.stdout, sys.stderr):        # Windows 콘솔(cp949)에서 한글이 깨지지 않게
    _s.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "backend"))

# 검증은 임시 데이터베이스에서 돌립니다.
# 예전에는 개발용 데이터베이스의 예시 사업(p1·p2)을 그대로 읽었는데,
# 실제로 쓰기 시작하면 그 사업들이 없어져서 검증이 통째로 실패했습니다.
# 여기서 시드를 새로 넣고 대조하므로 실제 데이터와 상관없이 언제나 돕니다.
_TMP = Path(tempfile.mkdtemp(prefix="bizdash-verify-"))
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_TMP}/verify.db"

from app.core.calc import calc_actual, calc_planned, calc_status  # noqa: E402
from app.core.config import KST                                    # noqa: E402
from app.core.periods import period_of                             # noqa: E402
from app.db.session import SessionLocal                            # noqa: E402
from app.models import Project                                     # noqa: E402

FAIL = False


def node(script: str) -> str:
    return subprocess.run(
        ["node", str(HERE / script)], capture_output=True, encoding="utf-8", check=True, cwd=HERE
    ).stdout


def head(title: str) -> None:
    print("\n" + "=" * 66)
    print(title)
    print("=" * 66)


def check(ok: bool, message: str) -> None:
    global FAIL
    if not ok:
        FAIL = True
    print(("  통과  " if ok else "  실패  ") + message)


# ---------------------------------------------------------------- 회차 계산
def verify_periods() -> None:
    head("1. 회차 계산 — 주간·격주·월간 × 900일")
    expected = node("js_periods.js").split("\n")

    start = None
    for p in SessionLocal().query(Project).all():
        if p.id == "p1":
            start = p.start
    start = start or datetime(2026, 6, 1).date()

    rows = []
    base = datetime(2026, 1, 1).date()
    for cycle in ["주간", "격주", "월간"]:
        for i in range(900):
            d = base + timedelta(days=i)
            per = period_of(cycle, start, d)
            rows.append(
                "\t".join([cycle, d.isoformat(), per.key,
                           per.start.isoformat(), per.end.isoformat(), per.label, per.full])
            )

    bad = [(a, b) for a, b in zip(expected, rows) if a != b]
    check(not bad, f"{len(rows)}건 대조 — 불일치 {len(bad)}건")
    for a, b in bad[:3]:
        print(f"      프로토타입: {a}\n      이식본    : {b}")


# ---------------------------------------------------------------- 대시보드 숫자
def verify_dashboard() -> None:
    head("2. 대시보드 숫자 — 진행률·상태·집행액·성과지표")
    expected = json.loads(node("js_calc.js"))

    db = SessionLocal()
    for e in expected:
        p = db.get(Project, e["id"])
        if p is None:
            check(False, f"{e['id']} 사업이 데이터베이스에 없습니다 (시드를 넣었나요?)")
            continue

        total, done = len(p.tasks), sum(1 for t in p.tasks if t.done)
        actual = calc_actual(total, done)
        planned = calc_planned(p.start, p.end)
        open_issues = [x for x in p.entries if x.issue.strip() and not x.issue_done]
        st = calc_status(actual, planned, bool(open_issues))
        spent = sum(s.amount for x in p.entries for s in x.spends)

        by_cat: dict[str, int] = {}
        for x in p.entries:
            for s in x.spends:
                by_cat[s.category] = by_cat.get(s.category, 0) + s.amount

        kpis = [
            {
                "name": k.name,
                "value": sum(kv.value for x in p.entries for kv in x.kpi_values if kv.kpi_name == k.name),
                "target": k.target,
            }
            for k in p.kpis
        ]

        got = {
            "actual": actual, "planned": planned, "diff": actual - planned,
            "status": st.label, "tasksDone": done, "tasksTotal": total,
            "spent": spent, "left": max(0, p.budget - spent),
            "openIssues": len(open_issues),
            "kpis": kpis, "byCat": dict(sorted(by_cat.items())),
        }
        for key, mine in got.items():
            check(expected_eq(e[key], mine), f"[{p.id}] {key}: {mine!r}")


def expected_eq(a: object, b: object) -> bool:
    return a == b


def prepare() -> None:
    """임시 데이터베이스에 프로토타입 시드를 넣습니다."""
    from app.db.session import Base, engine

    Base.metadata.create_all(engine)
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "seed" / "load_seed.py")],
        capture_output=True, encoding="utf-8", cwd=ROOT,
        env={**os.environ},
    )
    if r.returncode != 0:
        print("시드를 넣지 못했습니다:\n" + r.stdout + r.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    prepare()
    verify_periods()
    verify_dashboard()
    print("\n" + "=" * 66)
    print("검증 실패 항목이 있습니다" if FAIL else "모든 검증을 통과했습니다")
    sys.exit(1 if FAIL else 0)
