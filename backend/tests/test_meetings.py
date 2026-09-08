"""
회의록 — 사업비 지출 증빙(감사·정산)에 쓰는 문서.

양식에 있는 칸(시간·작성자·요청 및 예정 사항)이 실제로 문서까지 닿는지를
봅니다. 저장은 되는데 문서에는 안 찍히는 일이 이 기능에서 가장 아픕니다 —
정산 서류를 다 만들고 나서야 알게 됩니다.
"""
from __future__ import annotations

import io

from docx import Document

M = "/api/projects/t1/meetings"


def payload(**kw):
    body = {
        "title": "1차 콘텐츠 기획 회의",
        "metOn": "2026-09-08",
        "metStart": "14:00",
        "metEnd": "15:30",
        "place": "본관 3층 회의실",
        "writer": "홍길동",
        "attendees": ["김보건", "이디지"],
        "bullets": ["대상 학년 확정", "촬영 일정 조율"],
        "nextSteps": ["협조 공문 발송 (~9월 말)"],
        "memo": "",
        "amount": 320_000,
    }
    body.update(kw)
    return body


def 문서(client, mid: int) -> str:
    """만든 docx 의 글자를 모두 이어 붙여 돌려줍니다."""
    r = client.get(f"{M}/{mid}/docx")
    assert r.status_code == 200, r.text
    doc = Document(io.BytesIO(r.content))
    글 = []
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                글.append(cell.text)
    return "\n".join(글)


def test_시간_작성자_예정사항을_넣고_읽는다(client):
    d = client.post(M, json=payload()).json()
    assert d["metStart"] == "14:00"
    assert d["metEnd"] == "15:30"
    assert d["writer"] == "홍길동"
    assert d["nextSteps"] == ["협조 공문 발송 (~9월 말)"]


def test_문서에_시간과_작성자와_예정사항이_찍힌다(client):
    """
    저장은 되는데 문서에는 안 들어가는 일을 막습니다. 이 셋은 화면이 아니라
    docx 가 목적이라, 문서까지 봐야 실제로 된 것입니다.
    """
    mid = client.post(M, json=payload()).json()["id"]
    글 = 문서(client, mid)
    assert "14:00 ~ 15:30" in 글
    assert "홍길동" in 글
    assert "협조 공문 발송 (~9월 말)" in 글
    assert "대상 학년 확정" in 글


def test_종료_시각은_없어도_된다(client):
    """언제 끝났는지 모른 채 적는 일이 흔합니다. 물결표만 남으면 이상합니다."""
    mid = client.post(M, json=payload(metEnd="")).json()["id"]
    글 = 문서(client, mid)
    assert "14:00" in 글
    assert "~" not in 글.split("본관")[0]


def test_시간을_아예_안_적어도_된다(client):
    mid = client.post(M, json=payload(metStart="", metEnd="")).json()["id"]
    assert client.get(f"{M}/{mid}/docx").status_code == 200


def test_종료가_시작보다_빠르면_막는다(client):
    """그대로 두면 문서에 '15:30 ~ 14:00' 이 찍힙니다."""
    r = client.post(M, json=payload(metStart="15:30", metEnd="14:00"))
    assert r.status_code == 400
    assert "빠릅니다" in r.json()["detail"]


def test_종료만_적으면_막는다(client):
    """어느 쪽을 뜻하는지 알 수 없습니다."""
    r = client.post(M, json=payload(metStart="", metEnd="15:30"))
    assert r.status_code == 400


def test_시간_형식이_틀리면_막는다(client):
    """주소창으로 곧장 부르는 경우가 있어 서버에서도 봅니다."""
    for 나쁜값 in ("25:00", "14시", "1400", "14:75"):
        r = client.post(M, json=payload(metStart=나쁜값))
        assert r.status_code == 400, 나쁜값


def test_예정사항의_빈_줄은_걷어낸다(client):
    """화면에서 [+ 줄 추가] 만 누르고 안 적으면 문서에 빈 글머리가 찍힙니다."""
    d = client.post(M, json=payload(nextSteps=["할 일 하나", "  ", ""])).json()
    assert d["nextSteps"] == ["할 일 하나"]


def test_예전_회의록도_그대로_열린다(client):
    """
    새 칸이 없던 때에 저장된 회의록입니다. 마이그레이션이 빈 값을 채우므로
    문서 만들기가 깨지지 않아야 합니다.
    """
    mid = client.post(M, json=payload(
        metStart="", metEnd="", writer="", nextSteps=[])).json()["id"]
    글 = 문서(client, mid)
    assert "1차 콘텐츠 기획 회의" in 글 or "대상 학년 확정" in 글


def test_고칠_때도_새_칸이_남는다(client):
    mid = client.post(M, json=payload()).json()["id"]
    d = client.put(f"{M}/{mid}", json=payload(writer="김실무", metEnd="16:00")).json()
    assert d["writer"] == "김실무"
    assert d["metEnd"] == "16:00"
    assert "14:00 ~ 16:00" in 문서(client, mid)
