"""공고 조회 · 직접 등록 · 수집"""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query as Q
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.collector import runner  # noqa: F401  (수집 실행에 씁니다)
from app.core.security import require_session
from app.core.timeutil import kst_iso
from app.db.session import get_db
from app.models import Announcement, AnnouncementFavorite, AppSetting, CollectorRun
from app.services import announcements as svc

router = APIRouter(prefix="/api/announcements", tags=["announcements"],
                   dependencies=[Depends(require_session)])


def _split(v: str) -> list[str]:
    return [x.strip() for x in (v or "").split(",") if x.strip()]


def _date(v: str) -> date | None:
    v = (v or "").strip()
    try:
        return date.fromisoformat(v)
    except ValueError:
        return None


@router.get("")
def list_announcements(
    db: Session = Depends(get_db),
    tab: str = "all",
    q: str = "",
    sort: str = "due",
    ministries: str = "",
    amount: str = "all",
    include: str = "",
    page: int = Q(1, ge=1),
    size: int = Q(40, ge=1, le=200),
) -> dict[str, Any]:
    query = svc.Query(
        tab=tab, q=q, sort=sort, ministries=_split(ministries),
        amount=amount, include=_split(include), page=page, size=size,
    )
    out = svc.search(db, query)
    out["facets"] = svc.facets(db, query)
    return out


# ------------------------------------------------------------------ 관심(★)
@router.post("/{ann_id}/favorite")
def toggle_favorite(ann_id: str, db: Session = Depends(get_db)) -> dict[str, bool]:
    if db.get(Announcement, ann_id) is None:
        raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다.")
    row = db.get(AnnouncementFavorite, ann_id)
    if row is None:
        db.add(AnnouncementFavorite(announcement_id=ann_id))
        db.commit()
        return {"fav": True}
    db.delete(row)
    db.commit()
    return {"fav": False}


# ------------------------------------------------------------------ 직접 등록·수정·삭제
class AnnIn(BaseModel):
    title: str = ""
    ministry: str = ""
    agency: str = ""
    program: str = ""
    no: str = ""
    posted: str = ""
    openFrom: str = ""
    due: str = ""
    dueTime: str = ""
    amountEok: float = 0        # 화면은 억원, 저장은 원
    contact: str = ""
    url: str = ""


def _clean(body: AnnIn) -> dict[str, Any]:
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="공고명을 입력하세요.")
    open_from, due = _date(body.openFrom), _date(body.due)
    if not open_from:
        raise HTTPException(status_code=400, detail="접수 시작일을 입력하세요.")
    if not due:
        raise HTTPException(status_code=400, detail="접수 마감일을 입력하세요.")
    if due < open_from:
        raise HTTPException(status_code=400, detail="접수 마감일이 시작일보다 빠릅니다.")
    return {
        "title": title,
        "ministry": body.ministry.strip(),
        "agency": body.agency.strip(),
        "program": body.program.strip(),
        "no": body.no.strip(),
        "posted": _date(body.posted) or open_from,
        "open_from": open_from,
        "due": due,
        "due_time": body.dueTime.strip(),
        "amount": max(0, round(body.amountEok * 1e8)),
        "contact": body.contact.strip(),
        "url": body.url.strip(),
    }


@router.post("")
def create_announcement(body: AnnIn, db: Session = Depends(get_db)) -> dict[str, Any]:
    from app.collector.parse import uid

    data = _clean(body)
    row = Announcement(id=uid("manual", data["title"], data["open_from"]), source="manual", **data)
    while db.get(Announcement, row.id) is not None:
        row.id += "x"
    db.add(row)
    db.commit()
    return {"id": row.id}


@router.put("/{ann_id}")
def update_announcement(ann_id: str, body: AnnIn, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = db.get(Announcement, ann_id)
    if row is None:
        raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다.")
    for k, v in _clean(body).items():
        setattr(row, k, v)
    # 손으로 고친 공고는 다음 수집에서 덮어쓰지 않습니다
    row.source = "manual"
    db.commit()
    return {"id": row.id}


@router.delete("/{ann_id}")
def delete_announcement(ann_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    row = db.get(Announcement, ann_id)
    if row is None:
        raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다.")
    db.delete(row)
    db.commit()
    return {"deleted": ann_id}


# ------------------------------------------------------------------ 수집
collector_router = APIRouter(prefix="/api/collector", tags=["collector"],
                             dependencies=[Depends(require_session)])


@collector_router.get("/status")
def collector_status(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    마지막 수집이 언제 돌았고 몇 건 걷혔는지.
    수집이 조용히 멈춰 있는데 아무도 모르는 상황이 제일 위험합니다.
    """
    last = db.query(CollectorRun).order_by(CollectorRun.id.desc()).first()
    return {
        "last": None if last is None else {
            "startedAt": kst_iso(last.started_at),
            "finishedAt": kst_iso(last.finished_at),
            "ok": last.ok,
            "trigger": last.trigger,
            "added": last.added,
            "updated": last.updated,
            "totalSeen": last.total_seen,
            "detail": last.detail or {},
        },
    }


@collector_router.post("/run")
def collector_run(db: Session = Depends(get_db)) -> dict[str, Any]:
    """지금 수집 — 화면의 [지금 수집] 버튼"""
    return runner.run(db, trigger="manual")


# ------------------------------------------------------------------ 관심 조건
class AnnFilterIn(BaseModel):
    include: list[str] = Field(default_factory=list)
    ministries: list[str] = Field(default_factory=list)
    amount: str = "all"


filter_router = APIRouter(prefix="/api/settings", tags=["settings"],
                          dependencies=[Depends(require_session)])


@filter_router.patch("/ann-filter")
def set_ann_filter(body: AnnFilterIn, db: Session = Depends(get_db)) -> dict[str, Any]:
    value = {
        "include": [x.strip() for x in body.include if x.strip()],
        "ministries": body.ministries,
        "amount": body.amount if body.amount in ("all", *svc.AMOUNT_RANGES) else "all",
    }
    row = db.get(AppSetting, "ann_filter")
    if row is None:
        db.add(AppSetting(key="ann_filter", value=value))
    else:
        row.value = value
    db.commit()
    return value
