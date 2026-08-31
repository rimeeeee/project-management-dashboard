"""
프로토타입 시드 데이터를 데이터베이스로 옮깁니다.  ※ 개발용입니다.

실제 서비스에는 돌리지 마세요. 예시 사업 2건이 들어갑니다.
(실수로 돌렸다면 scripts/seed/clear_examples.py 로 지울 수 있습니다.)

    .venv/bin/python scripts/seed/load_seed.py           # 비어 있을 때만
    .venv/bin/python scripts/seed/load_seed.py --reset   # 지우고 다시 넣기

prototype-seed.json 은 프로토타입의 seedData() 함수를 그대로 실행해서 뽑은 것입니다
(scripts/seed/extract.js). 손으로 옮겨 적지 않았으므로 값이 달라질 여지가 없습니다.

프로토타입의 normalize() 가 하던 보정을 여기서 그대로 합니다.
  - 비목 중복 제거, 비어 있으면 기본 비목
  - 배정액이 없는 비목은 0 (임의로 나눠 채우지 않습니다 — 실제와 다른 잔액이 보이므로)
  - 단계별 내용은 5칸으로 맞춤
  - 금액이 0 이하인 집행 내역은 버림
  - 제목이 '(예시)' 로 시작하는 공고는 버림
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.periods import period_of                      # noqa: E402
from app.db.session import SessionLocal                      # noqa: E402
from app.models import (                                     # noqa: E402
    Announcement,
    EntryRevision,
    AppSetting,
    Project,
    ProjectCategory,
    ProjectKpi,
    ProjectStageNote,
    ProjectTask,
    ProjectTodo,
    ReportEntry,
    EntryKpiValue,
    EntrySpend,
)

SEED = Path(__file__).with_name("prototype-seed.json")

# 프로토타입 DEFAULT_CATEGORIES 와 같습니다
DEFAULT_CATEGORIES = ["인건비", "연구활동비", "장비·재료비", "여비", "회의·행사비", "외주용역비", "기타"]
STAGE_COUNT = 5   # 기획·착수·진행·마무리·완료


def iso(v: str | None) -> date | None:
    v = (v or "").strip()
    if not v:
        return None
    try:
        return date.fromisoformat(v)
    except ValueError:
        return None


def load(reset: bool) -> int:
    data = json.loads(SEED.read_text(encoding="utf-8"))
    db = SessionLocal()
    try:
        existing = db.query(Project).count() + db.query(Announcement).count()
        if existing and not reset:
            print(f"이미 데이터가 있습니다 ({existing}건). 다시 넣으려면 --reset 을 붙이세요.")
            return 1
        if reset:
            # 사업·공고를 지우면 딸린 줄(회차·집행·지표…)은 함께 지워집니다.
            for p in db.query(Project).all():
                db.delete(p)
            db.query(Announcement).delete()
            db.query(AppSetting).delete()
            # 이력은 회차를 지워도 남도록 만들어 두었습니다(감사 기록).
            # 시드를 다시 넣을 때는 예전 시험 기록이 섞이면 헷갈리므로 함께 지웁니다.
            db.query(EntryRevision).delete()
            db.commit()
            print("기존 데이터를 지웠습니다.")

        # ---------------- 사업 ----------------
        for order, p in enumerate(data["projects"]):
            start, end = iso(p["start"]), iso(p["end"])
            cycle = p.get("cycle") or "주간"

            proj = Project(
                id=p["id"],
                name=p["name"],
                agency=p.get("agency", ""),
                start=start,
                end=end,
                budget=int(p.get("budget") or 0),
                cycle=cycle,
                folder_url=(p.get("folderUrl") or "").strip(),
                stage=int(p.get("stage") or 0),
                sort_order=order,
                created_by="프로토타입 이관",
                updated_by="프로토타입 이관",
            )

            # 비목 — 중복 제거, 비어 있으면 기본 비목
            names: list[str] = []
            for c in p.get("categories") or []:
                c = str(c).strip()
                if c and c not in names:
                    names.append(c)
            if not names:
                names = DEFAULT_CATEGORIES.copy()
            cat_budgets = p.get("catBudgets") or {}
            for i, nm in enumerate(names):
                proj.categories.append(
                    ProjectCategory(
                        name=nm, budget_amount=int(cat_budgets.get(nm) or 0), sort_order=i
                    )
                )

            for i, t in enumerate(p.get("tasks") or []):
                proj.tasks.append(
                    ProjectTask(name=t["name"], done=bool(t.get("done")), sort_order=i)
                )

            for i, k in enumerate(p.get("kpis") or []):
                proj.kpis.append(
                    ProjectKpi(
                        name=k["name"],
                        unit=k.get("unit") or "건",
                        target=int(k.get("target") or 0),
                        sort_order=i,
                    )
                )

            notes = list(p.get("stageNotes") or [])[:STAGE_COUNT]
            notes += [""] * (STAGE_COUNT - len(notes))
            for i, note in enumerate(notes):
                proj.stage_notes.append(ProjectStageNote(stage_index=i, note=note or ""))

            for i, t in enumerate(p.get("todos") or []):
                if not str(t.get("text", "")).strip():
                    continue
                proj.todos.append(
                    ProjectTodo(
                        id=t["id"],
                        text=t["text"],
                        due=iso(t.get("due")),
                        done=bool(t.get("done")),
                        sort_order=i,
                        created_by="프로토타입 이관",
                    )
                )

            # ---------------- 보고 회차 ----------------
            for e in p.get("entries") or []:
                d = iso(e["date"])
                per = period_of(cycle, start, d)
                entry = ReportEntry(
                    period_key=per.key,
                    entry_date=d,
                    act=e.get("act") or "",
                    issue=e.get("issue") or "",
                    plan=e.get("plan") or "",
                    issue_done=bool(e.get("issueDone")),
                    entered_by="프로토타입 이관",
                    updated_by="프로토타입 이관",
                    version=1,
                )
                for i, s in enumerate(e.get("spends") or []):
                    amt = int(s.get("amt") or 0)
                    if amt <= 0:
                        continue      # 금액이 0 이하인 줄은 프로토타입도 버립니다
                    entry.spends.append(
                        EntrySpend(category=s.get("cat") or names[0], amount=amt, sort_order=i)
                    )
                for kname, kval in (e.get("kpi") or {}).items():
                    entry.kpi_values.append(
                        EntryKpiValue(kpi_name=kname, value=int(kval or 0))
                    )
                proj.entries.append(entry)

            db.add(proj)

        # ---------------- 공고 ----------------
        now = datetime.now(timezone.utc)
        seen: set[str] = set()
        skipped = 0
        for a in data.get("announcements") or []:
            title = str(a.get("title") or "").strip()
            if not title or title.startswith("(예시)"):
                skipped += 1
                continue
            aid = a.get("id")
            if not aid or aid in seen:
                skipped += 1
                continue
            seen.add(aid)
            db.add(
                Announcement(
                    id=aid,
                    ministry=a.get("ministry") or a.get("src") or "",
                    agency=a.get("agency") or "",
                    no=a.get("no") or "",
                    title=title,
                    program=a.get("program") or "",
                    posted=iso(a.get("posted")),
                    open_from=iso(a.get("openFrom")) or iso(a.get("posted")),
                    due=iso(a.get("due")),
                    due_time=a.get("dueTime") or "",
                    amount=int(a.get("amount") or 0),
                    contact=a.get("contact") or "",
                    url=a.get("url") or "",
                    source=a.get("source") or "manual",
                    collected_at=now,
                )
            )

        # ---------------- 화면 설정 ----------------
        f = data.get("annFilter") or {}
        db.add(
            AppSetting(
                key="ann_filter",
                value={
                    "include": f.get("include") or [],
                    "ministries": f.get("ministries") or [],
                    "amount": f.get("amount") or "all",
                },
                updated_by="프로토타입 이관",
            )
        )
        db.add(
            AppSetting(
                key="manual_url",
                value={"url": (data.get("manualUrl") or "").strip()},
                updated_by="프로토타입 이관",
            )
        )

        db.commit()
        if skipped:
            print(f"공고 {skipped}건은 제외했습니다 (제목 없음·(예시)·중복 id).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="기존 데이터를 지우고 다시 넣습니다")
    raise SystemExit(load(ap.parse_args().reset))
