"""보고 회차 저장·삭제, 그리고 입력 패널에서 즉시 저장되는 것들"""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.calc import STAGES, today
from app.core.periods import period_list, period_of
from app.core.security import require_session
from app.db.session import get_db
from app.models import Project, ProjectStageNote, ProjectTodo
from app.services import entries as svc
from app.services import projects as pjsvc

router = APIRouter(
    prefix="/api/projects/{project_id}",
    tags=["entries"],
    dependencies=[Depends(require_session)],
)


def get_project(project_id: str, db: Session = Depends(get_db)) -> Project:
    p = db.get(Project, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="사업을 찾을 수 없습니다.")
    return p


# ------------------------------------------------------------------ 회차 목록
@router.get("/periods")
def list_periods(p: Project = Depends(get_project)) -> list[dict[str, Any]]:
    """
    입력 패널의 회차 드롭다운. 오늘 회차부터 과거로 12개를 보여 주고,
    이미 입력된 회차인지 함께 알려 줍니다 (프로토타입과 같습니다).
    """
    have = {e.period_key: e for e in p.entries}
    out = []
    seen = set()
    for per in period_list(p.cycle, p.start, today(), 12):
        seen.add(per.key)
        out.append({
            "key": per.key, "label": per.label, "full": per.full,
            "date": per.start.isoformat(),
            "hasEntry": per.key in have,
            "version": have[per.key].version if per.key in have else 0,
        })
    # 목록 밖에 있는 오래된 회차도 수정할 수 있어야 합니다
    for e in sorted(p.entries, key=lambda x: x.entry_date, reverse=True):
        if e.period_key in seen:
            continue
        per = period_of(p.cycle, p.start, e.entry_date)
        out.append({
            "key": per.key, "label": per.label, "full": per.full,
            "date": per.start.isoformat(), "hasEntry": True, "version": e.version,
        })
    return out


# ------------------------------------------------------------------ 회차 저장
class SpendIn(BaseModel):
    cat: str = ""
    amt: int = 0


class EntryIn(BaseModel):
    spends: list[SpendIn] = Field(default_factory=list)
    kpi: dict[str, float] = Field(default_factory=dict)
    act: str = ""
    issue: str = ""
    plan: str = ""
    # 화면이 보고 있던 회차 번호. 0 이면 '아직 없는 회차'로 알고 있다는 뜻입니다.
    baseVersion: int = 0


@router.put("/entries/{period_key}")
def save_entry(
    period_key: str,
    body: EntryIn,
    response: Response,
    p: Project = Depends(get_project),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    # 회차 키가 이 사업의 것인지 확인합니다.
    # 목록에 없는 오래된 회차도 허용해야 하므로, 키에서 날짜를 되짚어 확인합니다.
    target = None
    for per in period_list(p.cycle, p.start, today(), 60):
        if per.key == period_key:
            target = per
            break
    if target is None:
        existing = next((e for e in p.entries if e.period_key == period_key), None)
        if existing is None:
            raise HTTPException(status_code=400, detail="이 사업의 회차가 아닙니다.")
        target = period_of(p.cycle, p.start, existing.entry_date)

    for s in body.spends:
        if s.amt < 0:
            raise HTTPException(status_code=400, detail="집행액은 0 이상의 숫자로 입력하세요.")
    for name, v in body.kpi.items():
        if v < 0:
            raise HTTPException(status_code=400, detail=f"성과지표 '{name}' 값을 0 이상으로 입력하세요.")

    data = svc.EntryInput(
        spends=[s.model_dump() for s in body.spends],
        kpi=body.kpi, act=body.act.strip(),
        issue=body.issue.strip(), plan=body.plan.strip(),
    )
    try:
        entry = svc.save_entry(db, p, period_key, target.start, data, body.baseVersion)
    except svc.SaveConflict as c:
        response.status_code = 409
        return c.payload()

    db.refresh(p)
    return {"entry": pjsvc._entry_out(p, entry), "project": pjsvc.detail(p)}


@router.delete("/entries/{period_key}")
def delete_entry(
    period_key: str,
    p: Project = Depends(get_project),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not svc.delete_entry(db, p, period_key):
        raise HTTPException(status_code=404, detail="그 회차를 찾을 수 없습니다.")
    db.refresh(p)
    return {"project": pjsvc.detail(p)}


@router.post("/entries/{period_key}/issue-toggle")
def toggle_issue(
    period_key: str,
    p: Project = Depends(get_project),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if svc.toggle_issue_done(db, p, period_key) is None:
        raise HTTPException(status_code=404, detail="확인사항이 있는 회차가 아닙니다.")
    db.refresh(p)
    return {"project": pjsvc.detail(p)}


@router.get("/entries/{period_key}/history")
def entry_history(
    period_key: str,
    p: Project = Depends(get_project),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """그 회차가 어떻게 바뀌어 왔는지. 지워진 회차의 기록도 남아 있습니다."""
    from app.core.timeutil import kst_iso
    from app.models import EntryRevision

    rows = (
        db.query(EntryRevision)
        .filter(EntryRevision.project_id == p.id, EntryRevision.period_key == period_key)
        .order_by(EntryRevision.revision_no.desc())
        .all()
    )
    return [
        {
            "revisionNo": r.revision_no,
            "action": r.action,
            "changedBy": r.changed_by,
            "changedAt": kst_iso(r.changed_at),
            "snapshot": r.snapshot,
        }
        for r in rows
    ]


# ------------------------------------------------------------------ 즉시 저장되는 것들
class StageIn(BaseModel):
    stage: int


@router.patch("/stage")
def set_stage(
    body: StageIn,
    p: Project = Depends(get_project),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not (0 <= body.stage < len(STAGES)):
        raise HTTPException(status_code=400, detail="진행 단계 값이 올바르지 않습니다.")
    p.stage = body.stage
    db.commit()
    db.refresh(p)
    return pjsvc.detail(p)


class StageNoteIn(BaseModel):
    index: int
    note: str = ""


@router.patch("/stage-note")
def set_stage_note(
    body: StageNoteIn,
    p: Project = Depends(get_project),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if not (0 <= body.index < len(STAGES)):
        raise HTTPException(status_code=400, detail="단계 번호가 올바르지 않습니다.")
    row = next((n for n in p.stage_notes if n.stage_index == body.index), None)
    if row is None:
        row = ProjectStageNote(project_id=p.id, stage_index=body.index)
        p.stage_notes.append(row)
    row.note = body.note.strip()
    db.commit()
    db.refresh(p)
    return pjsvc.detail(p)


class TaskIn(BaseModel):
    index: int
    done: bool


@router.patch("/task")
def set_task(
    body: TaskIn,
    p: Project = Depends(get_project),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    tasks = sorted(p.tasks, key=lambda t: t.sort_order)
    if not (0 <= body.index < len(tasks)):
        raise HTTPException(status_code=400, detail="추진과제 번호가 올바르지 않습니다.")
    tasks[body.index].done = body.done
    db.commit()
    db.refresh(p)
    return pjsvc.detail(p)


# ------------------------------------------------------------------ 할 일
class TodoIn(BaseModel):
    text: str
    due: str = ""


@router.post("/todos")
def add_todo(
    body: TodoIn,
    p: Project = Depends(get_project),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="할 일 내용을 적어 주세요.")
    due: date | None = None
    if body.due.strip():
        try:
            due = date.fromisoformat(body.due.strip())
        except ValueError:
            raise HTTPException(status_code=400, detail="기한 날짜가 올바르지 않습니다.") from None
    order = max((t.sort_order for t in p.todos), default=-1) + 1
    p.todos.append(
        ProjectTodo(
            id=f"t{int(today().toordinal())}-{order}-{abs(hash(text)) % 10000}",
            text=text, due=due, done=False, sort_order=order, )
    )
    db.commit()
    db.refresh(p)
    return pjsvc.detail(p)


@router.patch("/todos/{todo_id}")
def toggle_todo(
    todo_id: str,
    p: Project = Depends(get_project),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    t = next((x for x in p.todos if x.id == todo_id), None)
    if t is None:
        raise HTTPException(status_code=404, detail="할 일을 찾을 수 없습니다.")
    t.done = not t.done
    db.commit()
    db.refresh(p)
    return pjsvc.detail(p)


@router.delete("/todos/{todo_id}")
def remove_todo(
    todo_id: str,
    p: Project = Depends(get_project),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    t = next((x for x in p.todos if x.id == todo_id), None)
    if t is None:
        raise HTTPException(status_code=404, detail="할 일을 찾을 수 없습니다.")
    db.delete(t)
    db.commit()
    db.refresh(p)
    return pjsvc.detail(p)
