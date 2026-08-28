"""화면 설정 — 공고 관심 조건, 사업 매뉴얼 주소"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import require_session
from app.db.session import get_db
from app.models import AppSetting

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(require_session)])

DEFAULTS: dict[str, dict[str, Any]] = {
    "ann_filter": {"include": [], "ministries": [], "amount": "all"},
    "manual_url": {"url": ""},
}


@router.get("")
def read_settings(db: Session = Depends(get_db)) -> dict[str, Any]:
    stored = {s.key: s.value for s in db.query(AppSetting).all()}
    return {key: stored.get(key, default) for key, default in DEFAULTS.items()}
