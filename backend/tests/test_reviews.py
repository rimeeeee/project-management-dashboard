"""
검토중 사업 — 공고를 바로 '내 사업' 으로 올리지 않고 한 단계 거칩니다.

    공고  →  검토중  →  [지원완료]  →  내 사업
               └ 참여가능 / 부적합·불확실(사유)
"""
from __future__ import annotations

R = "/api/reviews"


def payload(**kw):
    body = {
        "name": "2026 스마트병원 선도모델",
        "agency": "보건복지부",
        "amount": 500_000_000,
        "due": "2026-10-15",
        "url": "https://example.test/a1",
        "verdict": "ok",
        "reason": "",
        "note": "",
    }
    body.update(kw)
    return body


def test_검토_목록에_담고_읽는다(client):
    d = client.post(R, json=payload()).json()
    assert d["verdict"] == "ok"
    assert d["amount"] == 500_000_000

    rows = client.get(R).json()
    assert [x["name"] for x in rows] == ["2026 스마트병원 선도모델"]


def test_사유_없이는_부적합으로_둘_수_없다(client):
    """
    나중에 비슷한 공고가 또 왔을 때 '그때 왜 안 했더라' 를 다시 따지지 않으려면
    까닭이 남아 있어야 합니다. 그래서 사유를 비워 두는 것을 막습니다.
    """
    r = client.post(R, json=payload(verdict="no"))
    assert r.status_code == 400
    assert "사유" in r.json()["detail"]

    ok = client.post(R, json=payload(verdict="no", reason="우리 사업 범위 밖입니다"))
    assert ok.status_code == 201
    assert ok.json()["reason"] == "우리 사업 범위 밖입니다"


def test_참여가능으로_되돌리면_사유는_지워진다(client):
    rid = client.post(R, json=payload(verdict="no", reason="예산이 맞지 않음")).json()["id"]
    back = client.put(f"{R}/{rid}", json=payload(verdict="ok", reason="예산이 맞지 않음"))
    assert back.json()["reason"] == ""      # 참여가능인데 사유가 남아 있으면 헷갈립니다


def test_같은_공고를_두_번_담지_않는다(client):
    """목록에 똑같은 줄이 쌓이면 어느 것이 최신인지 알 수 없어집니다."""
    assert client.post(R, json=payload(announcementId="a-1")).status_code == 201
    dup = client.post(R, json=payload(announcementId="a-1"))
    assert dup.status_code == 400
    assert "이미" in dup.json()["detail"]


def test_검토_항목을_지운다(client):
    rid = client.post(R, json=payload()).json()["id"]
    assert client.delete(f"{R}/{rid}").status_code == 204
    assert client.get(R).json() == []
