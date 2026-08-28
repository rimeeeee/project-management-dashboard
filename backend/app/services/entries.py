"""
보고 회차 저장 — 이 서비스의 핵심입니다.

프로토타입은 저장 버튼을 누르면 전체 데이터를 통째로 덮어썼습니다.
그래서 A 가 p1 회차를 저장하는 동안 B 가 p2 를 저장하면 B 의 저장이
A 의 내용을 통째로 지웠습니다.

여기서는 회차 한 줄만 건드립니다. 그리고 두 사람이 '같은 회차'를 동시에
고칠 때만 충돌로 봅니다. 그 경우에도 조용히 덮어쓰지 않고, 누가 언제
저장했는지 알려 준 뒤 사람이 정하게 합니다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.core.timeutil import kst_iso, kst_short
from app.core.periods import period_of
from app.models import EntryKpiValue, EntryRevision, EntrySpend, Project, ReportEntry
from app.services import projects as pjsvc


class SaveConflict(Exception):
    """
    다른 사람이 먼저 저장해 둔 경우.

    kind
      exists   — 화면은 '신규'로 알고 있었는데 그 사이 그 회차가 생겼습니다
      conflict — 화면이 들고 있던 내용이 이미 낡았습니다
    """

    def __init__(self, kind: str, entry: ReportEntry, project: Project) -> None:
        self.kind = kind
        self.entry = entry
        self.project = project
        super().__init__(kind)

    def payload(self) -> dict[str, Any]:
        who = self.entry.updated_by or self.entry.entered_by or "다른 사용자"
        when = kst_short(self.entry.updated_at)
        per = period_of(self.project.cycle, self.project.start, self.entry.entry_date)
        if self.kind == "exists":
            msg = f"{per.label} 회차는 이미 입력되어 있습니다."
        else:
            msg = f"이 회차는 방금 다른 분이 저장했습니다 ({who} · {when})."
        return {
            "kind": self.kind,
            "message": msg,
            "who": who,
            "when": when,
            "current": pjsvc._entry_out(self.project, self.entry),
        }


@dataclass
class EntryInput:
    spends: list[dict[str, Any]]
    kpi: dict[str, int]
    act: str
    issue: str
    plan: str


def _snapshot(p: Project, e: ReportEntry) -> dict[str, Any]:
    """바뀌기 전 내용을 그대로 담아 둡니다."""
    out = pjsvc._entry_out(p, e)
    out["createdAt"] = kst_iso(e.created_at)
    return out


def _next_revision_no(db: Session, project_id: str, period_key: str) -> int:
    last = (
        db.query(EntryRevision)
        .filter(EntryRevision.project_id == project_id, EntryRevision.period_key == period_key)
        .order_by(EntryRevision.revision_no.desc())
        .first()
    )
    return (last.revision_no + 1) if last else 1


def _apply(db: Session, entry: ReportEntry, data: EntryInput) -> None:
    entry.act = data.act
    entry.issue = data.issue
    entry.plan = data.plan

    # 확인사항 내용을 지웠다면 '해결됨' 표시도 함께 지웁니다.
    # 내용이 없는데 해결 표시만 남아 있으면 뜻이 통하지 않습니다.
    if not data.issue.strip():
        entry.issue_done = False

    entry.spends.clear()
    db.flush()
    for i, s in enumerate(data.spends):
        amt = int(s.get("amt") or 0)
        if amt <= 0:
            continue          # 금액이 없는 줄은 버립니다 (프로토타입과 같습니다)
        entry.spends.append(
            EntrySpend(category=str(s.get("cat") or ""), amount=amt, sort_order=i)
        )

    entry.kpi_values.clear()
    db.flush()
    for name, value in data.kpi.items():
        entry.kpi_values.append(EntryKpiValue(kpi_name=name, value=int(value or 0)))


def save_entry(
    db: Session,
    p: Project,
    period_key: str,
    entry_date: date,
    data: EntryInput,
    who: str,
    base_version: int,
) -> ReportEntry:
    """
    base_version
      0    — 화면은 '이 회차는 아직 없다'고 알고 있음
      N>0  — 화면이 N 번째 내용을 보고 고치는 중
    """
    existing = (
        db.query(ReportEntry)
        .filter(ReportEntry.project_id == p.id, ReportEntry.period_key == period_key)
        .one_or_none()
    )

    if existing is None:
        if base_version:
            # 고치려던 회차가 사라졌습니다 (다른 사람이 지웠습니다).
            # 새로 만들어 줍니다 — 사람이 방금 적은 내용을 버리는 편이 더 나쁩니다.
            pass
        entry = ReportEntry(
            project_id=p.id,
            period_key=period_key,
            entry_date=entry_date,
            entered_by=who,
            updated_by=who,
            version=1,
        )
        _apply(db, entry, data)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    if existing.version != base_version:
        raise SaveConflict("exists" if base_version == 0 else "conflict", existing, p)

    # 고치기 전 내용을 이력으로 남깁니다
    db.add(
        EntryRevision(
            entry_id=existing.id,
            project_id=p.id,
            period_key=period_key,
            revision_no=_next_revision_no(db, p.id, period_key),
            action="update",
            snapshot=_snapshot(p, existing),
            changed_by=who,
        )
    )
    _apply(db, existing, data)
    existing.updated_by = who
    existing.version += 1
    db.commit()
    db.refresh(existing)
    return existing


def delete_entry(db: Session, p: Project, period_key: str, who: str) -> bool:
    entry = (
        db.query(ReportEntry)
        .filter(ReportEntry.project_id == p.id, ReportEntry.period_key == period_key)
        .one_or_none()
    )
    if entry is None:
        return False

    # 지우기 전 내용을 남깁니다. 회차가 없어져도 이 기록은 남습니다.
    db.add(
        EntryRevision(
            entry_id=None,
            project_id=p.id,
            period_key=period_key,
            revision_no=_next_revision_no(db, p.id, period_key),
            action="delete",
            snapshot=_snapshot(p, entry),
            changed_by=who,
        )
    )
    db.delete(entry)
    db.commit()
    return True


def toggle_issue_done(db: Session, p: Project, period_key: str, who: str) -> ReportEntry | None:
    entry = (
        db.query(ReportEntry)
        .filter(ReportEntry.project_id == p.id, ReportEntry.period_key == period_key)
        .one_or_none()
    )
    if entry is None or not entry.issue.strip():
        return None
    entry.issue_done = not entry.issue_done
    entry.updated_by = who
    entry.version += 1
    db.commit()
    db.refresh(entry)
    return entry
