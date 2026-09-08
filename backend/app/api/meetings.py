"""
회의록 — 사업비 지출 증빙(감사·정산)에 쓰는 문서.

사업에 매달려 있습니다. 회의록은 그 사업 예산을 쓴 근거이므로, 사업과
떨어지면 '어느 사업 회의비인지' 가 사라져 증빙 구실을 못 합니다.

문서 만들기(docx)와 AI 초안은 따로 둡니다. 여기서는 회의록 자체를
넣고 빼고 고치는 것만 다룹니다.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.entries import get_project
from app.core.security import require_session
from app.core.timeutil import kst_iso
from app.core.config import ROOT
from app.db.session import get_db
from app.models import Meeting, MeetingPhoto, Project

router = APIRouter(
    prefix="/api/projects/{project_id}/meetings",
    tags=["meetings"],
    dependencies=[Depends(require_session)],
)


def bad(msg: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


class MeetingIn(BaseModel):
    title: str = ""
    metOn: str = ""
    metStart: str = ""              # "HH:MM", 안 적어도 됩니다
    metEnd: str = ""
    place: str = ""
    writer: str = ""
    attendees: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)
    nextSteps: list[str] = Field(default_factory=list)
    memo: str = ""
    amount: int = 0


def _out(m: Meeting) -> dict[str, Any]:
    return {
        "id": m.id,
        "title": m.title,
        "metOn": m.met_on.isoformat(),
        "metStart": m.met_start,
        "metEnd": m.met_end,
        "place": m.place,
        "writer": m.writer,
        "attendees": list(m.attendees or []),
        "bullets": list(m.bullets or []),
        "nextSteps": list(m.next_steps or []),
        "memo": m.memo,
        "amount": m.amount,
        # 파일 이름은 서버가 정합니다. 화면에서도 같은 규칙으로 미리 보여 주는데,
        # 두 곳이 달라지면 '미리 본 이름과 받은 파일 이름이 다르다' 가 됩니다.
        "fileName": file_name(m),
        "fileNameWithAmount": file_name(m, with_amount=True),
        "createdAt": kst_iso(m.created_at),
        "photos": [
            {"id": ph.id, "name": ph.original_name, "url": f"/api/photos/{ph.stored_name}"}
            for ph in m.photos
        ],
    }


def file_name(m: Meeting, with_amount: bool = True) -> str:
    """
    YYMMDD_회의록_회의명.docx   (금액을 넣기로 하면 뒤에 _금액원 이 붙습니다)

    정산할 때 폴더 목록이 곧 지출 내역이 되도록 금액을 붙입니다.
    금액이 없으면(0) 그 부분은 빠집니다.
    """
    날짜 = m.met_on.strftime("%y%m%d")
    제목 = _safe(m.title) or "회의"
    if with_amount and m.amount > 0:
        return f"{날짜}_회의록_{제목}_{m.amount:,}원.docx"
    return f"{날짜}_회의록_{제목}.docx"


def _safe(s: str) -> str:
    """파일 이름에 쓸 수 없는 글자를 걷어냅니다."""
    for ch in '\\/:*?"<>|':
        s = s.replace(ch, "")
    return " ".join(s.split()).strip()


def _time(s: str, 이름: str) -> str:
    """
    "HH:MM" 만 받습니다. 빈 값은 그대로 둡니다.

    화면의 time 입력이 이 꼴로 보내지만, 주소창으로 곧장 부르는 경우도
    있어 여기서 한 번 더 봅니다. 엉뚱한 글자가 그대로 문서에 찍히면
    증빙 문서가 우스워집니다.
    """
    s = s.strip()
    if not s:
        return ""
    if not re.fullmatch(r"([01][0-9]|2[0-3]):[0-5][0-9]", s):
        raise bad(f"{이름}을 24시간 형식(예: 14:00)으로 적어 주세요.")
    return s


def _clean(body: MeetingIn) -> dict[str, Any]:
    title = " ".join(body.title.split()).strip()
    if not title:
        raise bad("회의명을 입력하세요.")
    try:
        met_on = date.fromisoformat(body.metOn)
    except ValueError:
        raise bad("회의 날짜를 확인하세요.") from None
    if body.amount < 0:
        raise bad("금액은 0 이상으로 입력하세요.")

    # 빈 줄과 중복 이름은 여기서 걷어냅니다. 화면에서 지웠는데 빈 칸이
    # 남아 문서에 빈 bullet 이 찍히는 일을 막습니다.
    attendees: list[str] = []
    for nm in body.attendees:
        nm = " ".join(str(nm).split()).strip()
        if nm and nm not in attendees:
            attendees.append(nm)
    bullets = [b.strip() for b in body.bullets if str(b).strip()]
    next_steps = [s.strip() for s in body.nextSteps if str(s).strip()]

    start = _time(body.metStart, "시작 시각")
    end = _time(body.metEnd, "종료 시각")
    # 끝이 앞서면 적다가 잘못 누른 것입니다. 그대로 두면 문서에
    # "15:30 ~ 14:00" 이 찍힙니다. 자정을 넘기는 회의는 없다고 봅니다.
    if start and end and end < start:
        raise bad("종료 시각이 시작 시각보다 빠릅니다.")
    # 끝만 적혀 있으면 어느 쪽을 뜻하는지 알 수 없습니다.
    if end and not start:
        raise bad("시작 시각을 먼저 적어 주세요.")

    return {
        "title": title,
        "met_on": met_on,
        "met_start": start,
        "met_end": end,
        "place": body.place.strip(),
        "writer": " ".join(body.writer.split()).strip()[:60],
        "attendees": attendees,
        "bullets": bullets,
        "next_steps": next_steps,
        "memo": body.memo.strip(),
        "amount": int(body.amount),
    }


@router.get("")
def list_meetings(
    p: Project = Depends(get_project), db: Session = Depends(get_db)
) -> list[dict[str, Any]]:
    return [_out(m) for m in p.meetings]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_meeting(
    body: MeetingIn, p: Project = Depends(get_project), db: Session = Depends(get_db)
) -> dict[str, Any]:
    m = Meeting(project_id=p.id, **_clean(body))
    db.add(m)
    db.commit()
    db.refresh(m)
    return _out(m)


def _get(db: Session, p: Project, meeting_id: int) -> Meeting:
    m = (
        db.query(Meeting)
        .filter(Meeting.id == meeting_id, Meeting.project_id == p.id)
        .one_or_none()
    )
    if m is None:
        raise HTTPException(status_code=404, detail="회의록을 찾지 못했습니다.")
    return m


@router.put("/{meeting_id}")
def update_meeting(
    meeting_id: int,
    body: MeetingIn,
    p: Project = Depends(get_project),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    m = _get(db, p, meeting_id)
    for k, v in _clean(body).items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return _out(m)


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(
    meeting_id: int, p: Project = Depends(get_project), db: Session = Depends(get_db)
) -> None:
    db.delete(_get(db, p, meeting_id))
    db.commit()


# 사진은 파일로 둡니다(백업 파일이 커지지 않게).
PHOTO_DIR = ROOT / "data" / "uploads"


@router.get("/{meeting_id}/docx")
def download_docx(
    meeting_id: int,
    withAmount: bool = True,
    p: Project = Depends(get_project),
    db: Session = Depends(get_db),
) -> Response:
    """회의록을 docx 로 내려보냅니다. 한글(HWP)에서도 열립니다."""
    from urllib.parse import quote

    from app.services.minutes_doc import build

    m = _get(db, p, meeting_id)
    data = build(m, PHOTO_DIR)
    name = file_name(m, with_amount=withAmount)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            # 한글 파일 이름은 filename* 로 보내야 브라우저가 제대로 받습니다.
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}",
        },
    )


# ------------------------------------------------------------------ AI 초안
class DraftIn(BaseModel):
    title: str = ""
    memo: str = ""
    place: str = ""


@router.post("/draft")
def draft(
    body: DraftIn, p: Project = Depends(get_project)
) -> dict[str, Any]:
    """
    회의명과 메모로 회의내용 bullet 초안을 받습니다.

    저장하지 않습니다. 화면에서 고친 뒤 저장을 눌러야 남습니다.
    사람이 손대기 전 결과를 그대로 문서에 넣지 않게 하려는 것입니다.
    """
    from app.services.minutes_ai import AIUnavailable
    from app.services.minutes_ai import draft as ai_draft

    title = " ".join(body.title.split()).strip()
    if not title:
        raise bad("회의명을 먼저 입력하세요.")
    try:
        return ai_draft(title, body.memo, body.place)
    except AIUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


class NextStepsIn(BaseModel):
    title: str = ""
    bullets: list[str] = Field(default_factory=list)
    memo: str = ""


@router.post("/next-steps")
def next_steps(body: NextStepsIn, p: Project = Depends(get_project)) -> dict[str, Any]:
    """
    지금 적혀 있는 회의내용만 보고 요청 및 예정 사항을 다시 씁니다.

    초안을 받은 뒤 회의내용을 손보는 일이 잦은데, 그때 할 일도 함께
    바뀌어야 앞뒤가 맞습니다. 그래서 따로 부를 수 있게 둡니다.
    """
    from app.services.minutes_ai import AIUnavailable, draft_next_steps

    title = " ".join(body.title.split()).strip()
    if not title:
        raise bad("회의명을 먼저 입력하세요.")
    if not [b for b in body.bullets if str(b).strip()]:
        raise bad("회의내용을 먼저 채워 주세요.")
    try:
        return {"nextSteps": draft_next_steps(title, body.bullets, body.memo)}
    except AIUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.post("/title-suggestions")
def suggest_titles(body: DraftIn, p: Project = Depends(get_project)) -> dict[str, Any]:
    """회의명 다듬기 제안. 화면에 칩으로 보여 주고 고르면 바뀝니다."""
    from app.services.minutes_ai import AIUnavailable, title_suggestions

    title = " ".join(body.title.split()).strip()
    if not title:
        raise bad("회의명을 먼저 입력하세요.")
    try:
        return {"titles": title_suggestions(title)}
    except AIUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


# ------------------------------------------------------------------ 사진
# 올릴 수 있는 그림 종류. 확장자만 보고 믿지 않고 실제 내용을 함께 봅니다.
IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}
MAX_PHOTO_BYTES = 10 * 1024 * 1024      # 10MB


@router.post("/{meeting_id}/photos", status_code=status.HTTP_201_CREATED)
async def upload_photo(
    meeting_id: int,
    file: UploadFile = File(...),
    p: Project = Depends(get_project),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    회의 사진을 올립니다. 파일은 data/uploads/ 에 두고 표에는 이름만 남깁니다.

    사진을 데이터베이스에 넣으면 백업(pg_dump) 파일이 급격히 커지고 되돌리는
    데도 오래 걸립니다. 파일은 파일로 두는 편이 낫습니다.
    """
    import secrets

    m = _get(db, p, meeting_id)

    ext = IMAGE_TYPES.get((file.content_type or "").lower())
    if ext is None:
        raise bad("그림 파일만 올릴 수 있습니다 (jpg · png · gif · webp).")

    data = await file.read()
    if len(data) > MAX_PHOTO_BYTES:
        raise bad("사진 한 장은 10MB 까지 올릴 수 있습니다.")
    if not data:
        raise bad("빈 파일입니다.")

    # 올린 사람이 쓰던 이름을 그대로 저장 이름으로 쓰지 않습니다.
    # 같은 이름끼리 덮어쓰고, 이름에 경로가 섞여 들어올 수도 있습니다.
    stored = f"{secrets.token_hex(16)}{ext}"
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    (PHOTO_DIR / stored).write_bytes(data)

    ph = MeetingPhoto(
        meeting_id=m.id,
        stored_name=stored,
        original_name=(file.filename or "")[:255],
        sort_order=len(m.photos),
    )
    db.add(ph)
    db.commit()
    db.refresh(ph)
    return {"id": ph.id, "name": ph.original_name, "url": f"/api/photos/{ph.stored_name}"}


@router.delete("/{meeting_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(
    meeting_id: int,
    photo_id: int,
    p: Project = Depends(get_project),
    db: Session = Depends(get_db),
) -> None:
    m = _get(db, p, meeting_id)
    ph = next((x for x in m.photos if x.id == photo_id), None)
    if ph is None:
        raise HTTPException(status_code=404, detail="사진을 찾지 못했습니다.")
    # 표에서 지우고 파일도 함께 지웁니다. 파일만 남으면 아무도 모르게 쌓입니다.
    (PHOTO_DIR / ph.stored_name).unlink(missing_ok=True)
    db.delete(ph)
    db.commit()


# 사진 보여 주기 — 로그인한 사람만 볼 수 있어야 하므로 정적 파일로 열지 않고
# 여기서 내보냅니다. data/uploads 를 그대로 공개하면 주소만 알면 누구나 봅니다.
photo_router = APIRouter(prefix="/api/photos", tags=["meetings"],
                         dependencies=[Depends(require_session)])


@photo_router.get("/{stored_name}")
def get_photo(stored_name: str) -> Response:
    from fastapi.responses import FileResponse

    # 이름에 경로가 섞여 들어와 다른 폴더를 읽는 일이 없게 이름만 씁니다.
    safe = Path(stored_name).name
    f = PHOTO_DIR / safe
    if not f.is_file():
        raise HTTPException(status_code=404, detail="사진을 찾지 못했습니다.")
    return FileResponse(f)
