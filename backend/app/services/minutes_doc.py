"""
회의록 docx 만들기.

docs/회의록양식/회의록양식.docx 를 열어 빈칸만 채웁니다.
서식을 코드로 다시 그리지 않는 이유는, 그렇게 하면 실제 쓰는 양식과 조금씩
어긋나고 양식이 바뀔 때마다 코드를 고쳐야 하기 때문입니다. 양식이 바뀌면
그 파일만 새로 넣으면 됩니다.

양식 표는 6행 4열이고 아래처럼 생겼습니다.

    0행  일시      | (값)            | 시간   | (값)
    1행  장소      | (값)            | 작성자 | (값)
    2행  참석자    | (값 · 3칸 병합)
    3행  (4칸 병합 — 비어 있는 줄)
    4행  회의 내용 | (bullet · 3칸 병합)
    5행  요청 및   | (값 · 3칸 병합)
         예정 사항
"""
from __future__ import annotations

import copy
import io
from pathlib import Path

from docx import Document
from docx.shared import Cm

from app.core.config import ROOT
from app.models import Meeting

TEMPLATE = ROOT / "docs" / "회의록양식" / "회의록양식.docx"

# 사진을 넣을 때 쓰는 최대 너비(cm). 본문 폭에 맞춥니다.
# 높이는 정하지 않습니다 — python-docx 가 원본 비율대로 계산합니다.
PHOTO_MAX_W = Cm(15.0)


def _put(cell, text: str) -> None:
    """
    칸의 첫 문단에 값만 넣습니다.

    글꼴·크기·가운데 맞춤 같은 서식은 양식이 이미 갖고 있으므로,
    문단을 새로 만들지 않고 있던 문단의 글자만 바꿔 끼웁니다.
    """
    para = cell.paragraphs[0]
    for r in list(para.runs)[1:]:
        r._element.getparent().remove(r._element)
    if para.runs:
        para.runs[0].text = text
    else:
        para.add_run(text)
    # 두 번째 문단부터는 양식에 있던 빈 줄이라 그대로 둡니다.


def _put_bullets(cell, bullets: list[str]) -> None:
    """
    회의 내용 칸에 줄을 채웁니다.

    양식의 'List Paragraph' 문단을 본으로 삼아 필요한 만큼 복제합니다.
    새로 만들면 양식이 정해 둔 들여쓰기·글머리 기호를 잃습니다.
    """
    본 = next((p for p in cell.paragraphs if p.style.name == "List Paragraph"), None)
    if 본 is None:                       # 양식이 바뀌어 본이 없으면 그냥 적습니다
        for b in bullets:
            cell.add_paragraph(b)
        return

    # 본 문단을 첫 줄로 쓰고, 나머지는 복제해서 뒤에 붙입니다.
    앞 = 본
    for i, b in enumerate(bullets):
        if i == 0:
            _put_text(본, b)
        else:
            새 = copy.deepcopy(본._p)
            앞._p.addnext(새)
            from docx.text.paragraph import Paragraph
            앞 = Paragraph(새, 본._parent)
            _put_text(앞, b)

    # 양식에 있던 빈 List Paragraph 는 지웁니다(빈 글머리 기호가 찍힙니다).
    for p in list(cell.paragraphs):
        if p.style.name == "List Paragraph" and not p.text.strip():
            p._p.getparent().remove(p._p)


def _put_text(para, text: str) -> None:
    for r in list(para.runs)[1:]:
        r._element.getparent().remove(r._element)
    if para.runs:
        para.runs[0].text = text
    else:
        para.add_run(text)


def 시간문구(m: Meeting) -> str:
    """
    "14:00 ~ 15:30" · "14:00" · "" 중 하나.

    끝나는 시각은 안 적어도 됩니다. 회의가 길어져 언제 끝났는지 모르는 채로
    적는 일이 흔한데, 그때 억지로 채우게 하면 없는 숫자를 지어내게 됩니다.
    """
    시작, 끝 = (m.met_start or "").strip(), (m.met_end or "").strip()
    if 시작 and 끝:
        return f"{시작} ~ {끝}"
    return 시작 or 끝


def build(m: Meeting, photo_dir: Path) -> bytes:
    doc = Document(str(TEMPLATE))
    t = doc.tables[0]

    참석 = ", ".join(m.attendees or []) or "-"
    인원 = len(m.attendees or [])

    _put(t.rows[0].cells[1], m.met_on.strftime("%Y. %m. %d."))
    _put(t.rows[0].cells[3], 시간문구(m) or "-")
    _put(t.rows[1].cells[1], m.place or "-")
    _put(t.rows[1].cells[3], m.writer or "-")
    _put(t.rows[2].cells[1], 참석)

    # '참석자 (총 n명)' 의 n 을 실제 인원으로 바꿉니다.
    # 글자가 run 여러 개로 쪼개져 있어("(", "총 ", "n", "명", ")") run 하나만
    # 봐서는 못 찾습니다. 문단 전체를 이어 붙여 바꾸고 첫 run 에 되돌립니다.
    for para in t.rows[2].cells[0].paragraphs:
        whole = "".join(r.text for r in para.runs)
        if "n" in whole and "명" in whole:
            _put_text(para, whole.replace("n", str(인원)))

    _put_bullets(t.rows[4].cells[1], m.bullets or ["-"])

    # 요청 및 예정 사항. 회의내용과 같은 글머리 기호를 씁니다 —
    # 한 문서 안에서 목록 모양이 두 가지면 어수선해 보입니다.
    _put_bullets(t.rows[5].cells[1], m.next_steps or ["-"])

    # 사진은 표 뒤에 붙입니다. 원본 비율을 지키려고 너비만 정합니다.
    photos = [photo_dir / ph.stored_name for ph in m.photos]
    photos = [f for f in photos if f.exists()]
    if photos:
        doc.add_paragraph()
        for f in photos:
            para = doc.add_paragraph()
            try:
                para.add_run().add_picture(str(f), width=PHOTO_MAX_W)
            except Exception:      # noqa: BLE001
                # 사진 하나가 깨졌다고 문서 전체를 못 만들면 곤란합니다.
                para.add_run(f"(사진을 넣지 못했습니다: {f.name})")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
