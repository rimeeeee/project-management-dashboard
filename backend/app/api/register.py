"""
사업 등록 · 수정 · 삭제.

프로토타입 submitRegister() / editProject() / deleteProject() 의 규칙을 그대로 옮겼습니다.
확인 순서와 문구도 같습니다 — 실무에서 익숙해진 순서라 바꾸지 않습니다.

한 가지만 서버에서 더 챙깁니다.
입력 내역이 있는 사업은 보고 주기를 바꾸지 못하게 막습니다. 화면에서도 막고 있지만,
화면의 disabled 는 마음만 먹으면 풀 수 있어서 서버에서 다시 확인합니다.
주기가 바뀌면 이미 저장된 회차의 키(W…/B…/M…)가 다른 기간을 가리키게 됩니다.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.periods import BIWEEKLY, MONTHLY, WEEKLY
from app.core.security import require_session
from app.db.session import get_db
from app.models import (
    AppSetting,
    Project,
    ProjectCategory,
    ProjectKpi,
    ProjectStageNote,
    ProjectTask,
)
from app.services import projects as pjsvc

router = APIRouter(prefix="/api/projects", tags=["register"], dependencies=[Depends(require_session)])

STAGE_COUNT = 5
CYCLES = (WEEKLY, BIWEEKLY, MONTHLY)


class KpiIn(BaseModel):
    name: str = ""
    target: float = 0
    unit: str = "건"


class TaskIn(BaseModel):
    name: str = ""


class CategoryIn(BaseModel):
    name: str = ""
    allocated: int = 0


class ProjectIn(BaseModel):
    name: str = ""
    agency: str = ""
    folderUrl: str = ""
    start: str = ""
    end: str = ""
    # 화면에서는 억원으로 받고, 여기서 원으로 바꿔 저장합니다.
    budgetEok: float = 0
    cycle: str = WEEKLY
    kpis: list[KpiIn] = Field(default_factory=list)
    tasks: list[TaskIn] = Field(default_factory=list)
    categories: list[CategoryIn] = Field(default_factory=list)


class Cleaned(BaseModel):
    name: str
    agency: str
    folder_url: str
    start: date
    end: date
    budget: int
    cycle: str
    kpis: list[KpiIn]
    tasks: list[str]
    categories: list[CategoryIn]


def bad(msg: str) -> HTTPException:
    return HTTPException(status_code=400, detail=msg)


def clean(body: ProjectIn) -> Cleaned:
    """프로토타입과 같은 순서로 확인합니다. 문구도 그대로입니다."""
    name = body.name.strip()
    if not name:
        raise bad("사업명을 입력하세요.")

    try:
        start = date.fromisoformat(body.start)
        end = date.fromisoformat(body.end)
    except ValueError:
        raise bad("사업 기간을 확인하세요 (시작일 < 종료일).") from None
    if not (start < end):
        raise bad("사업 기간을 확인하세요 (시작일 < 종료일).")

    if body.budgetEok <= 0:
        raise bad("총 사업비는 0보다 큰 숫자(억원)로 입력하세요.")
    budget = round(body.budgetEok * 1e8)      # 억 → 원

    if body.cycle not in CYCLES:
        raise bad("보고 주기가 올바르지 않습니다.")

    # 이름이 있고 목표가 0보다 큰 지표만 받습니다
    kpis: list[KpiIn] = []
    seen_kpi: set[str] = set()
    for k in body.kpis:
        nm = k.name.strip()
        if not nm or k.target <= 0 or nm in seen_kpi:
            continue
        seen_kpi.add(nm)
        kpis.append(KpiIn(name=nm, target=k.target, unit=k.unit.strip() or "건"))

    tasks = [t.name.strip() for t in body.tasks if t.name.strip()]

    cats: list[CategoryIn] = []
    seen_cat: set[str] = set()
    for c in body.categories:
        nm = c.name.strip()
        if not nm or nm in seen_cat:
            continue
        seen_cat.add(nm)
        cats.append(CategoryIn(name=nm, allocated=max(0, c.allocated)))

    # 확인 순서도 프로토타입과 같습니다 (비목 → 추진과제 → 성과지표)
    if not cats:
        raise bad("예산 비목을 1개 이상 입력하세요.")
    if not tasks:
        raise bad("추진과제를 1개 이상 입력하세요.")
    if not kpis:
        raise bad("성과지표를 1개 이상 입력하세요.")

    return Cleaned(
        name=name, agency=body.agency.strip(), folder_url=body.folderUrl.strip(),
        start=start, end=end, budget=budget, cycle=body.cycle,
        kpis=kpis, tasks=tasks, categories=cats,
    )


def _set_basics(p: Project, c: Cleaned) -> None:
    p.name, p.agency, p.folder_url = c.name, c.agency, c.folder_url
    p.start, p.end, p.budget, p.cycle = c.start, c.end, c.budget, c.cycle


def _set_lists(db: Session, p: Project, c: Cleaned, done_by_name: dict[str, bool]) -> None:
    """
    지표 · 추진과제 · 비목을 지우고 다시 넣습니다.

    지우고 넣는 사이에 flush() 가 없으면, 지우는 문이 나가기 전에 넣는 문이 먼저
    나가서 같은 이름이 잠깐 두 개가 되어 UNIQUE 제약에 걸립니다.
    """
    p.kpis.clear()
    p.tasks.clear()
    p.categories.clear()
    db.flush()

    p.kpis.extend(
        ProjectKpi(name=k.name, unit=k.unit, target=k.target, sort_order=i)
        for i, k in enumerate(c.kpis)
    )
    # 같은 이름의 과제는 완료 체크 상태를 유지합니다
    p.tasks.extend(
        ProjectTask(name=nm, done=done_by_name.get(nm, False), sort_order=i)
        for i, nm in enumerate(c.tasks)
    )
    p.categories.extend(
        ProjectCategory(name=x.name, budget_amount=x.allocated, sort_order=i)
        for i, x in enumerate(c.categories)
    )


@router.post("")
def create_project(body: ProjectIn, db: Session = Depends(get_db)) -> dict[str, Any]:
    c = clean(body)
    p = Project(
        id=f"p{int(datetime.now().timestamp() * 1000)}",
        stage=0,
        sort_order=db.query(Project).count(),
    )
    _set_basics(p, c)
    _set_lists(db, p, c, {})
    # 등록 화면에서 받지 않는 값입니다. 비워 두면 화면을 그리다 오류가 납니다.
    p.stage_notes.extend(ProjectStageNote(stage_index=i, note="") for i in range(STAGE_COUNT))
    db.add(p)
    db.commit()
    db.refresh(p)
    return pjsvc.detail(p)


@router.put("/{project_id}")
def update_project(project_id: str, body: ProjectIn, db: Session = Depends(get_db)) -> dict[str, Any]:
    p = db.get(Project, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="사업을 찾을 수 없습니다.")

    c = clean(body)

    if p.entries:
        # 회차 키가 이미 저장되어 있으므로 계산 기준을 바꿀 수 없습니다.
        if c.cycle != p.cycle:
            raise bad("입력 내역이 있어 보고 주기는 변경할 수 없습니다.")
        # 격주 회차 키는 '사업 시작일부터 몇 번째'입니다. 시작일이 바뀌면 어긋납니다.
        if p.cycle == BIWEEKLY and c.start != p.start:
            raise bad("입력 내역이 있어 격주 회차 기준일은 변경할 수 없습니다.")

    done_by_name = {t.name: t.done for t in p.tasks}
    _set_basics(p, c)
    _set_lists(db, p, c, done_by_name)
    db.commit()
    db.refresh(p)
    return pjsvc.detail(p)


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    p = db.get(Project, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="사업을 찾을 수 없습니다.")
    name = p.name
    db.delete(p)
    db.commit()
    return {"deleted": project_id, "name": name}


# ------------------------------------------------------------------ 사업 매뉴얼 주소
class ManualIn(BaseModel):
    url: str = ""


settings_router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(require_session)])


@settings_router.patch("/manual-url")
def set_manual_url(body: ManualIn, db: Session = Depends(get_db)) -> dict[str, str]:
    """
    노션 등 사업 매뉴얼 문서 주소를 하나 저장해 두고 메뉴에서 바로 엽니다.
    http(s) 가 없으면 붙여 줍니다 — 주소만 적어 넣는 경우가 많습니다.
    """
    url = body.url.strip()
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url
    row = db.get(AppSetting, "manual_url")
    if row is None:
        row = AppSetting(key="manual_url", value={"url": url})
        db.add(row)
    else:
        row.value = {"url": url}
    db.commit()
    return {"url": url}
