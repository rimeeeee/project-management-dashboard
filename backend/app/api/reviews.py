"""
검토중 사업 — 지원할지 말지 따져 보는 단계.

공고를 보고 바로 '내 사업' 으로 올리면 실제로 지원하지 않은 것까지 섞여
진행률·예산이 엉킵니다. 그래서 한 단계를 둡니다.

    공고  →  검토중  →  (지원완료)  →  내 사업
               └ 참여가능 / 부적합·불확실

부적합으로 접었을 때는 사유를 남깁니다. 나중에 비슷한 공고가 또 왔을 때
'그때 왜 안 했더라' 를 다시 따지지 않기 위해서입니다.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import require_session
from app.core.timeutil import kst_iso
from app.db.session import get_db
from app.models import Review

router = APIRouter(
    prefix="/api/reviews", tags=["reviews"], dependencies=[Depends(require_session)]
)

VERDICTS = {"ok", "no"}          # 참여가능 / 부적합·불확실


def bad(msg: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


class ReviewIn(BaseModel):
    name: str = ""
    agency: str = ""
    amount: int = 0
    due: str = ""
    url: str = ""
    verdict: str = "ok"
    reason: str = ""
    note: str = ""
    announcementId: str | None = None


def _out(r: Review) -> dict[str, Any]:
    return {
        "id": r.id,
        "name": r.name,
        "agency": r.agency,
        "amount": r.amount,
        "due": r.due.isoformat() if r.due else "",
        "url": r.url,
        "verdict": r.verdict,
        "reason": r.reason,
        "note": r.note,
        "announcementId": r.announcement_id,
        "createdAt": kst_iso(r.created_at),
    }


def _clean(body: ReviewIn) -> dict[str, Any]:
    name = " ".join(body.name.split()).strip()
    if not name:
        raise bad("사업명을 입력하세요.")
    if body.verdict not in VERDICTS:
        raise bad("검토 결과가 올바르지 않습니다.")

    due: date | None = None
    if body.due.strip():
        try:
            due = date.fromisoformat(body.due.strip())
        except ValueError:
            raise bad("마감일을 확인하세요.") from None

    reason = body.reason.strip()
    # 부적합으로 접으면 까닭을 반드시 남깁니다. 나중에 되짚어 볼 수 없으면
    # 같은 공고를 두고 매번 처음부터 다시 따지게 됩니다.
    if body.verdict == "no" and not reason:
        raise bad("부적합·불확실로 두려면 사유를 적어 주세요.")
    if body.verdict == "ok":
        reason = ""          # 참여가능으로 되돌리면 사유는 지웁니다

    return {
        "name": name,
        "agency": body.agency.strip(),
        "amount": max(0, int(body.amount)),
        "due": due,
        "url": body.url.strip(),
        "verdict": body.verdict,
        "reason": reason,
        "note": body.note.strip(),
        "announcement_id": (body.announcementId or None),
    }


@router.get("")
def list_reviews(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.query(Review).order_by(Review.created_at.desc()).all()
    return [_out(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_review(body: ReviewIn, db: Session = Depends(get_db)) -> dict[str, Any]:
    data = _clean(body)

    # 같은 공고를 두 번 올리지 않습니다. 목록에 똑같은 줄이 쌓이면
    # 어느 것이 최신인지 알 수 없어집니다.
    aid = data["announcement_id"]
    if aid:
        already = db.query(Review).filter(Review.announcement_id == aid).one_or_none()
        if already is not None:
            raise bad("이미 검토 목록에 있는 공고입니다.")

    r = Review(**data)
    db.add(r)
    db.commit()
    db.refresh(r)
    return _out(r)


def _get(db: Session, review_id: int) -> Review:
    r = db.get(Review, review_id)
    if r is None:
        raise HTTPException(status_code=404, detail="검토 항목을 찾지 못했습니다.")
    return r


@router.put("/{review_id}")
def update_review(
    review_id: int, body: ReviewIn, db: Session = Depends(get_db)
) -> dict[str, Any]:
    r = _get(db, review_id)
    for k, v in _clean(body).items():
        setattr(r, k, v)
    db.commit()
    db.refresh(r)
    return _out(r)


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(review_id: int, db: Session = Depends(get_db)) -> None:
    db.delete(_get(db, review_id))
    db.commit()
