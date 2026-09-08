"""
회의록 docx 만들기.

증빙 문서라 양식이 정해져 있습니다.
  회의록 / 회의명 / 일시 / 장소 / 참 석 자 / 회의내용(bullet)

한글(HWP)에서도 열립니다. hwpx 로 바로 만들지 않는 이유는, 파이썬에서
hwpx 를 제대로 다룰 수 있는 라이브러리가 사실상 없기 때문입니다.
"""
from __future__ import annotations

import io
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

from app.models import Meeting

# 한글 문서에서 흔히 쓰는 글꼴. 없는 PC 에서는 비슷한 글꼴로 대체됩니다.
FONT = "맑은 고딕"

# 사진을 넣을 때 쓰는 최대 너비(cm). 본문 폭에 맞춥니다.
PHOTO_MAX_W = Cm(15.0)


def _set_font(run, size: int, bold: bool = False) -> None:
    run.font.name = FONT
    run.font.size = Pt(size)
    run.bold = bold
    # 한글은 eastAsia 글꼴을 따로 지정해야 제대로 적용됩니다.
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    rfonts.set(
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia", FONT
    )


def build(m: Meeting, photo_dir: Path) -> bytes:
    doc = Document()

    # 여백 — 증빙 문서라 넉넉하지 않게, 한 장에 많이 담기도록 둡니다.
    for s in doc.sections:
        s.top_margin = s.bottom_margin = Cm(2.0)
        s.left_margin = s.right_margin = Cm(2.2)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_font(title.add_run("회 의 록"), 20, bold=True)
    doc.add_paragraph()

    # 머리 정보는 표로 둡니다. 줄글로 적으면 항목이 밀려 읽기 어렵습니다.
    머리 = [
        ("회 의 명", m.title),
        ("일     시", m.met_on.strftime("%Y년 %m월 %d일")),
        ("장     소", m.place or "-"),
        ("참 석 자", ", ".join(m.attendees or []) or "-"),
    ]
    table = doc.add_table(rows=len(머리), cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (k, v) in enumerate(머리):
        table.rows[i].cells[0].width = Cm(3.2)
        table.rows[i].cells[1].width = Cm(12.8)
        for cell, text, bold in ((table.rows[i].cells[0], k, True),
                                 (table.rows[i].cells[1], v, False)):
            para = cell.paragraphs[0]
            _set_font(para.add_run(text), 11, bold=bold)

    doc.add_paragraph()
    본문제목 = doc.add_paragraph()
    _set_font(본문제목.add_run("회의내용"), 12, bold=True)

    if m.bullets:
        for b in m.bullets:
            para = doc.add_paragraph(style="List Bullet")
            _set_font(para.add_run(b), 11)
    else:
        para = doc.add_paragraph()
        _set_font(para.add_run("-"), 11)

    # 사진은 본문 뒤에 붙입니다. 원본 비율을 지키려고 너비만 정하고
    # 높이는 비워 둡니다 — python-docx 가 비율에 맞춰 계산합니다.
    photos = [photo_dir / ph.stored_name for ph in m.photos]
    photos = [f for f in photos if f.exists()]
    if photos:
        doc.add_paragraph()
        사진제목 = doc.add_paragraph()
        _set_font(사진제목.add_run("회의 사진"), 12, bold=True)
        for f in photos:
            para = doc.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            try:
                para.add_run().add_picture(str(f), width=PHOTO_MAX_W)
            except Exception:      # noqa: BLE001
                # 사진 하나가 깨졌다고 문서 전체를 못 만들면 곤란합니다.
                _set_font(para.add_run(f"(사진을 넣지 못했습니다: {f.name})"), 10)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
