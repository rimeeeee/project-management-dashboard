"""사업 조회"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import require_session
from app.db.session import get_db
from app.models import Project
from app.services import projects as svc

router = APIRouter(prefix="/api/projects", tags=["projects"], dependencies=[Depends(require_session)])


@router.get("")
def list_projects(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.query(Project).order_by(Project.sort_order, Project.id).all()
    return [svc.summary(p) for p in rows]


@router.get("/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    p = db.get(Project, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="사업을 찾을 수 없습니다.")
    return svc.detail(p)
